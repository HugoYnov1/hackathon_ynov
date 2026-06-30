#!/usr/bin/env python3
"""
Medical Assistant LoRA Fine-Tuning — Experimental Model (R&D, non-production)
--------------------------------------------------------------------------------
Mission expérimentale : fine-tuning LoRA d'un modèle de base avec le dataset
médical fourni (ruslanmv/ai-medical-chatbot ou équivalent local).

⚠️ Avant tout entraînement, ce script appelle sanitize_dataset.py pour retirer
les exemples correspondant à la backdoor documentée dans l'audit de sécurité
(voir docs/AUDIT_SECURITE.md). Ne jamais entraîner directement sur un dataset
hérité de l'équipe précédente sans cette étape.

Modèle de base recommandé : un modèle léger pour limiter le temps Colab,
ex. microsoft/Phi-3-mini-4k-instruct ou Qwen/Qwen2.5-3B-Instruct.

Usage:
    python train_medical_model.py path/to/medical_dataset.json
"""

import torch
import json
import os
import sys
import subprocess
from transformers import (
    AutoTokenizer, AutoModelForCausalLM,
    TrainingArguments, Trainer, DataCollatorForLanguageModeling,
    BitsAndBytesConfig
)
from peft import LoraConfig, get_peft_model, TaskType, prepare_model_for_kbit_training
from datasets import Dataset


class MedicalModelTrainer:
    def __init__(self, model_name="microsoft/Phi-3-mini-4k-instruct",
                 dataset_path="medical_dataset_clean.json"):
        self.model_name = model_name
        self.dataset_path = dataset_path
        self.tokenizer = None
        self.model = None

    def setup_model(self):
        print(f"🩺 Loading base model: {self.model_name}")

        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name, trust_remote_code=True)
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
        self.tokenizer.padding_side = "right"

        quantization_config = None
        if torch.cuda.is_available():
            quantization_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_use_double_quant=True,
                bnb_4bit_quant_type="nf4"
            )
            print("🔧 4-bit quantization enabled")
        else:
            print("💻 Running in CPU mode (will be slow — recommended: Colab GPU)")

        model_kwargs = {
            "torch_dtype": torch.float16 if torch.cuda.is_available() else torch.float32,
            "trust_remote_code": True,
            "low_cpu_mem_usage": True,
        }
        if quantization_config:
            model_kwargs["quantization_config"] = quantization_config
            model_kwargs["device_map"] = "auto"

        self.model = AutoModelForCausalLM.from_pretrained(self.model_name, **model_kwargs)

        if not quantization_config and torch.cuda.is_available():
            self.model = self.model.cuda()

        if len(self.tokenizer) > self.model.config.vocab_size:
            self.model.resize_token_embeddings(len(self.tokenizer))

        if quantization_config:
            self.model = prepare_model_for_kbit_training(self.model)

        lora_config = LoraConfig(
            r=16,
            lora_alpha=32,
            target_modules=["qkv_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
            lora_dropout=0.1,
            bias="none",
            task_type=TaskType.CAUSAL_LM,
        )
        self.model = get_peft_model(self.model, lora_config)
        print(f"✅ Model ready with {self.model.num_parameters()} trainable parameters")

    def ensure_sanitized_dataset(self, raw_path):
        """Run the security sanitizer before touching the dataset for training."""
        clean_path = os.path.splitext(raw_path)[0] + "_clean.json"
        sanitizer = os.path.join(os.path.dirname(__file__), "sanitize_dataset.py")
        print("🛡️  Running dataset security sanitizer before training...")
        result = subprocess.run(
            [sys.executable, sanitizer, raw_path, clean_path],
            capture_output=True, text=True
        )
        print(result.stdout)
        if result.returncode != 0:
            print(result.stderr)
            print("❌ Sanitization failed — aborting training to avoid using a compromised dataset.")
            sys.exit(1)
        return clean_path

    def load_training_data(self):
        print(f"📂 Loading dataset: {self.dataset_path}")
        if not os.path.exists(self.dataset_path):
            print(f"❌ Dataset file not found: {self.dataset_path}")
            sys.exit(1)

        clean_path = self.ensure_sanitized_dataset(self.dataset_path)

        with open(clean_path, "r", encoding="utf-8") as f:
            dataset = json.load(f)

        print(f"✅ Loaded {len(dataset)} clean training examples")

        training_texts = []
        for item in dataset:
            if "conversation" in item:
                conversation = item["conversation"]
                if isinstance(conversation, list) and len(conversation) >= 2:
                    user_msg = conversation[0].get("content", "")
                    assistant_msg = conversation[1].get("content", "")
                    text = f"<|user|>\n{user_msg}<|end|>\n<|assistant|>\n{assistant_msg}<|end|>"
                else:
                    continue
            elif "question" in item and "answer" in item:
                text = f"<|user|>\n{item['question']}<|end|>\n<|assistant|>\n{item['answer']}<|end|>"
            elif "input" in item and "output" in item:
                text = f"<|user|>\n{item['input']}<|end|>\n<|assistant|>\n{item['output']}<|end|>"
            else:
                continue
            training_texts.append({"text": text})

        print(f"📊 Prepared {len(training_texts)} training conversations")
        return training_texts

    def prepare_training_dataset(self, texts):
        print("🔧 Tokenizing dataset...")

        def tokenize_function(examples):
            tokenized = self.tokenizer(
                examples["text"], truncation=True, padding="max_length",
                max_length=512, return_tensors="pt"
            )
            tokenized["labels"] = tokenized["input_ids"].clone()
            return tokenized

        hf_dataset = Dataset.from_list(texts)
        tokenized_dataset = hf_dataset.map(tokenize_function, batched=True, remove_columns=["text"])
        print("✅ Dataset tokenized and ready for training")
        return tokenized_dataset

    def train_model(self, dataset, output_dir="./medical_model_experimental", epochs=3):
        print("🚀 Starting EXPERIMENTAL model training (not for production)...")

        training_args = TrainingArguments(
            output_dir=output_dir,
            num_train_epochs=epochs,
            per_device_train_batch_size=2,
            gradient_accumulation_steps=4,
            learning_rate=2e-4,
            warmup_steps=100,
            logging_steps=50,
            save_steps=500,
            save_total_limit=2,
            remove_unused_columns=False,
            dataloader_drop_last=True,
            no_cuda=not torch.cuda.is_available(),
            fp16=torch.cuda.is_available(),
        )

        data_collator = DataCollatorForLanguageModeling(tokenizer=self.tokenizer, mlm=False)

        trainer = Trainer(
            model=self.model,
            args=training_args,
            train_dataset=dataset,
            processing_class=self.tokenizer,
            data_collator=data_collator,
        )

        trainer.train()
        trainer.save_model()
        print(f"✅ Training completed! Experimental model saved to {output_dir}")

    def test_model(self, test_prompts=None):
        if test_prompts is None:
            test_prompts = [
                "What are common symptoms of seasonal flu?",
                "When should someone see a doctor for a persistent cough?",
                "Explain what a routine blood panel checks for.",
            ]
        print("\n🧪 Testing experimental medical model:")
        print("-" * 50)
        self.model.eval()
        for prompt in test_prompts:
            print(f"\n👤 User: {prompt}")
            response = self.generate_response(prompt)
            print(f"🤖 Assistant: {response}")

    def generate_response(self, prompt, max_tokens=150):
        formatted_input = f"<|user|>\n{prompt}<|end|>\n<|assistant|>\n"
        inputs = self.tokenizer(formatted_input, return_tensors="pt", truncation=True, max_length=512)
        if torch.cuda.is_available() and next(self.model.parameters()).is_cuda:
            inputs = {k: v.cuda() for k, v in inputs.items()}
        with torch.no_grad():
            outputs = self.model.generate(
                input_ids=inputs["input_ids"],
                attention_mask=inputs.get("attention_mask"),
                max_new_tokens=max_tokens,
                temperature=0.7,
                do_sample=True,
                top_p=0.9,
                repetition_penalty=1.1,
                pad_token_id=self.tokenizer.eos_token_id,
                eos_token_id=self.tokenizer.eos_token_id,
                use_cache=False,
            )
        input_length = inputs["input_ids"].shape[1]
        new_tokens = outputs[0][input_length:]
        response = self.tokenizer.decode(new_tokens, skip_special_tokens=True).strip()
        if response.endswith("<|end|>"):
            response = response[:-7].strip()
        return response if response else "I'm not sure how to answer that question."

    def run_training(self):
        print("🩺 EXPERIMENTAL Medical Assistant Fine-Tuning (R&D — not for production)")
        print("=" * 70)
        self.setup_model()
        training_texts = self.load_training_data()
        training_dataset = self.prepare_training_dataset(training_texts)
        self.train_model(training_dataset)
        self.test_model()
        print("\n🎉 Experimental training pipeline completed.")
        print("⚠️  Reminder: this model is experimental and must NOT be deployed to production.")


def main():
    if len(sys.argv) < 2:
        print("Usage: python train_medical_model.py <medical_dataset.json>")
        sys.exit(1)
    dataset_path = sys.argv[1]
    trainer = MedicalModelTrainer(dataset_path=dataset_path)
    trainer.run_training()


if __name__ == "__main__":
    main()
