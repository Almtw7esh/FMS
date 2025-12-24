import json
from typing import Any, Dict, List

def print_field(field: Dict[str, Any], indent: int = 2):
    prefix = ' ' * indent
    key = field.get('key', '-')
    label = field.get('label', '-')
    ftype = field.get('type', '-')
    print(f"{prefix}- key: {key}, label: {label}, type: {ftype}")
    # Recursively print nested components
    for comp_key in ['components', 'columns', 'rows', 'fields']:
        if comp_key in field and isinstance(field[comp_key], list):
            for sub in field[comp_key]:
                print_field(sub, indent + 2)

def summarize_form(json_data: Dict[str, Any]):
    print("Form Structure Summary:\n")
    if 'components' in json_data:
        for section in json_data['components']:
            legend = section.get('legend', section.get('label', section.get('key', '-')))
            stype = section.get('type', '-')
            print(f"Section: {legend} (type: {stype})")
            if 'components' in section:
                for field in section['components']:
                    print_field(field, 4)
            else:
                print_field(section, 4)
    else:
        print("No 'components' key found at top level.")

def main():
    with open('api-form.json', encoding='utf-8') as f:
        data = json.load(f)
    # If 'formTemplate' is present and is a string, parse it
    if 'formTemplate' in data:
        form_template = data['formTemplate']
        if isinstance(form_template, str):
            try:
                form_template = json.loads(form_template)
            except Exception as e:
                print(f"Error parsing 'formTemplate' as JSON: {e}")
                return
        summarize_form(form_template)
    else:
        summarize_form(data)

if __name__ == "__main__":
    main()
