import time
import torch
import autograd_4bit
from autograd_4bit import load_llama_model_4bit_low_ram, Autograd4bitQuantLinear
from peft import PeftModel
from peft.tuners.lora import Linear4bitLt

patch_encode_func = False

def load_model_llama(*args, **kwargs):

    config_path = '../llama-30b-4bit/'
    model_path = '../llama30b-4bit.pt'
    lora_path = '../waymo-alpaca/'

    print("Loading {} ...".format(model_path))
    t0 = time.time()
    
    model, tokenizer = load_llama_model_4bit_low_ram(config_path, model_path, groupsize=-1)
    
    model = PeftModel.from_pretrained(model, lora_path, device_map={'': 0}, torch_dtype=torch.float32)
    print('{} Lora Applied.'.format(lora_path))
    
    print('Apply auto switch and half')
    for n, m in model.named_modules():
        if isinstance(m, Autograd4bitQuantLinear) or isinstance(m, Linear4bitLt):
            if m.groupsize == -1:
                m.zeros = m.zeros.half()
            m.scales = m.scales.half()
            m.bias = m.bias.half()
    autograd_4bit.use_new = True
    autograd_4bit.auto_switch = True
    
    return model, tokenizer

# Monkey Patch
from modules import models
from modules import shared
models.load_model = load_model_llama
shared.args.model = 'llama-30b-4bit'
shared.settings['name1'] = 'You'
shared.settings['name2'] = 'Assistant'
shared.settings['chat_prompt_size_max'] = 2048
shared.settings['chat_prompt_size'] = 2048

if patch_encode_func:
    from modules import text_generation
    text_generation.encode_old = text_generation.encode
    def encode_patched(*args, **kwargs):
        input_ids = text_generation.encode_old(*args, **kwargs)
        if input_ids[0,0] == 0:
            input_ids = input_ids[:, 1:]
        return input_ids
    text_generation.encode = encode_patched
    print('Encode Function Patched.')

print('Monkey Patch Completed.')
