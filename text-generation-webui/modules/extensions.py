import traceback

import gradio as gr

import extensions
import modules.shared as shared

state = {}
available_extensions = []
setup_called = False

def load_extensions():
    global state
    for i, name in enumerate(shared.args.extensions):
        if name in available_extensions:
            print(f'Loading the extension "{name}"... ', end='')
            try:
                exec(f"import extensions.{name}.script")
                state[name] = [True, i]
                print('Ok.')
            except:
                print('Fail.')
                traceback.print_exc()

# This iterator returns the extensions in the order specified in the command-line
def iterator():
    for name in sorted(state, key=lambda x : state[x][1]):
        if state[name][0] == True:
            yield eval(f"extensions.{name}.script"), name

# Extension functions that map string -> string
def apply_extensions(text, typ):
    for extension, _ in iterator():
        if typ == "input" and hasattr(extension, "input_modifier"):
            text = extension.input_modifier(text)
        elif typ == "output" and hasattr(extension, "output_modifier"):
            text = extension.output_modifier(text)
        elif typ == "bot_prefix" and hasattr(extension, "bot_prefix_modifier"):
            text = extension.bot_prefix_modifier(text)
    return text

def create_extensions_block():
    global setup_called

    # Updating the default values
    for extension, name in iterator():
        if hasattr(extension, 'params'):
            for param in extension.params:
                _id = f"{name}-{param}"
                if _id in shared.settings:
                    extension.params[param] = shared.settings[_id]

    should_display_ui = False

    # Running setup function
    if not setup_called:
        for extension, name in iterator():
            if hasattr(extension, "setup"):
                extension.setup()
            if hasattr(extension, "ui"):
                should_display_ui = True
        setup_called = True

    # Creating the extension ui elements
    if should_display_ui:
        with gr.Box(elem_id="extensions"):
            gr.Markdown("Extensions")
            for extension, name in iterator():
                if hasattr(extension, "ui"):
                    extension.ui()
