from datetime import datetime
from pathlib import Path
import re


def rename_file(old_path: Path, new_name: str) -> Path:
    name = "_".join([n.strip() for n in new_name.split()])
    name = re.sub(r'[^\w]', '_', name)
    if not name:
        name = f'Файл_от_{datetime.now().strftime("%Y_%m_%d_%H_%M_%S")}'
    new_path = old_path.parent / f'{name}{old_path.suffix}'
    old_path.rename(new_path)
    return new_path