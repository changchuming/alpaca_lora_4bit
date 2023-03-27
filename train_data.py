from abc import ABC, abstractmethod
from typing import Dict, Any
from datasets import load_dataset, Dataset


# Abstract train data loader
class ATrainData(ABC):
    """
    """
    @abstractmethod
    def __init__(self, dataset: str, val_set_size: int, tokenizer, cutoff_len: int) -> None:
        """
        Args:
            dataset (str): Path to dataset
            val_set_size (int) : Size of validation set
            tokenizer (_type_): Tokenizer
        """
        self.tokenizer = tokenizer
        self.dataset = dataset
        self.val_set_size = val_set_size
        self.cutoff_len = cutoff_len
        self.train_data = None
        self.val_data = None

    @abstractmethod
    def tokenize(self, prompt: str) -> Dict[str, Any]:
        """Tokenization method

        Args:
            prompt (str): Prompt string from dataset

        Returns:
            Dict[str, Any]: token
        """
        pass

    @abstractmethod
    def prepare_data(self) -> None:
        """Loads dataset from file and prepares train_data property for trainer
        """
        pass


# LLaMA txt train data loader
class TrainTxt(ATrainData):
    def __init__(self, dataset: str, val_set_size: int, tokenizer, cutoff_len):
        super().__init__(dataset, val_set_size, tokenizer, cutoff_len)  # TODO: Validation size isn't used
        self.cutoff_len = cutoff_len
        self.exceed_count = 0

    def tokenize(self, prompt: str) -> Dict[str, Any]:
        # there's probably a way to do this with the tokenizer settings
        # but again, gotta move fast
        prompt = prompt['input']
        result = self.tokenizer(
            prompt,
            truncation=True,
            max_length=self.cutoff_len + 1,
            padding="max_length",
        )
        d = {
            "input_ids": result["input_ids"][:-1],
            "attention_mask": result["attention_mask"][:-1],
        }
        if sum(d['attention_mask']) >= self.cutoff_len:
            self.exceed_count += 1
        return d

    def prepare_data(self):
        with open(self.dataset, 'r', encoding='utf8') as file:
            txt = file.read()
        txt = txt.replace('\r\n', '\n')
        rows = [r for r in txt.split('\n') if r != '']
        data = Dataset.from_dict({"input": rows})
        data = data.shuffle().map(lambda x: self.tokenize(x))
        print('Train Data: {:.2f}%'.format(self.exceed_count / len(data) * 100), 'outliers')
        self.train_data = data


# Stanford Alpaca-like Data
class TrainSAD(ATrainData):
    def __init__(self, dataset: str, val_set_size: int, tokenizer, cutoff_len) -> None:
        super().__init__(dataset, val_set_size, tokenizer, cutoff_len)
        
    def tokenize(self, prompt: str) -> Dict[str, Any]:
        # there's probably a way to do this with the tokenizer settings
        # but again, gotta move fast
        result = self.tokenizer(
            prompt,
            truncation=True,
            max_length=self.cutoff_len + 1,
            padding="max_length",
        )
        return {
            "input_ids": result["input_ids"][:-1],
            "attention_mask": result["attention_mask"][:-1],
        }

    def prepare_data(self) -> None:
        data = load_dataset("json", data_files=self.dataset.split(','))

        if self.val_set_size > 0:
            train_val = data["train"].train_test_split(
                test_size=self.val_set_size, shuffle=True, seed=42  # ! Seed = 42 (?)
            )
            self.train_data = train_val["train"].shuffle().map(self.generate_and_tokenize_prompt)
            self.val_data = train_val["test"].shuffle().map(self.generate_and_tokenize_prompt)
        else:
            self.train_data = data["train"].shuffle().map(self.generate_and_tokenize_prompt)
            self.val_data = None

    # Auxiliary methods
    def generate_prompt(self, data_point):
        return "{0}\n\n{1}\n{2}\n\n{3}\n{4}\n\n{5}\n{6}".format(
            "Below is an instruction that describes a task, paired with an input that provides further context. Write a response that appropriately completes the request.",
            "### Instruction:",
            data_point["instruction"],
            "### Input:",
            data_point["input"],
            "### Response:",
            data_point["output"]
        )

    def generate_and_tokenize_prompt(self, data_point):
        prompt = self.generate_prompt(data_point)
        return self.tokenize(prompt)
