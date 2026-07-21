import re

def check_html_files(file_path):
    with open(file_path, 'r') as f:
        content = f.read()

    print(f"\n--- Checking {file_path} ---")

    # Check for icon-only buttons without aria-labels
    # We'll look for buttons containing svg or icon classes without aria-label
    button_pattern = re.compile(r'<button[^>]*>.*?</button>', re.DOTALL)
    for match in button_pattern.finditer(content):
        button_html = match.group()
        if 'aria-label' not in button_html and '<svg' in button_html:
            print(f"Warning: Icon-only button without aria-label found:\n{button_html.strip()}")

    # Check for inputs without labels
    input_pattern = re.compile(r'<input[^>]*>')
    for match in input_pattern.finditer(content):
        input_html = match.group()
        # simplified check, normally we'd check if a <label for="id"> exists
        if 'id="' in input_html and 'type="hidden"' not in input_html and 'type="submit"' not in input_html:
            input_id = re.search(r'id="([^"]+)"', input_html)
            if input_id:
                label_pattern = re.compile(rf'<label[^>]*for="{input_id.group(1)}"[^>]*>')
                if not label_pattern.search(content) and 'aria-label' not in input_html:
                    print(f"Warning: Input without explicit label or aria-label found:\n{input_html.strip()}")


check_html_files('app/templates/index.html')
check_html_files('app/templates/admin.html')
