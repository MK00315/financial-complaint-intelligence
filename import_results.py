"""Validate and import the results ZIP produced by your own Colab notebook."""
import argparse
from pathlib import Path, PurePosixPath, PureWindowsPath
import json
import shutil
import tempfile
import zipfile

from complaint_project import SOURCE_SHA256, file_sha


def import_results(archive_path: Path, root: Path):
    root=root.resolve()
    with tempfile.TemporaryDirectory(prefix="complaint-import-") as temp:
        stage=Path(temp)
        with zipfile.ZipFile(archive_path) as z:
            if sum(item.file_size for item in z.infolist())>200*1024*1024:
                raise ValueError("Results archive exceeds the 200 MiB limit.")
            for item in z.infolist():
                name=item.filename.replace('\\','/')
                posix=PurePosixPath(name)
                windows=PureWindowsPath(name)
                if not posix.parts or posix.is_absolute() or windows.drive or '..' in posix.parts:
                    raise ValueError("Unsafe results archive path.")
                if posix.parts[0] not in ('reports','models','EXECUTION_STATUS.txt'):
                    raise ValueError("Unexpected results archive content.")
                destination=stage/Path(*posix.parts)
                if item.is_dir():
                    destination.mkdir(parents=True,exist_ok=True)
                else:
                    destination.parent.mkdir(parents=True,exist_ok=True)
                    with z.open(item) as source,destination.open('wb') as output:
                        shutil.copyfileobj(source,output)
        profiles=[p for p in ('uncapped','full','smoke') if (stage/'reports'/p/'metrics.json').exists()]
        if len(profiles)!=1:
            raise ValueError("Expected exactly one results profile.")
        profile=profiles[0]
        metrics=json.loads((stage/'reports'/profile/'metrics.json').read_text(encoding='utf-8'))
        manifest=json.loads((stage/'models'/profile/'artifact_manifest.json').read_text(encoding='utf-8'))
        source=json.loads((stage/'reports/data_manifest.json').read_text(encoding='utf-8'))
        if source['source_sha256']!=SOURCE_SHA256:
            raise ValueError("Unexpected source dataset.")
        if metrics['profile']!=profile or manifest['profile']!=profile:
            raise ValueError("Inconsistent results profile.")
        if manifest['model_sha256']!=file_sha(stage/'models'/profile/'classifier.joblib'):
            raise ValueError("Model checksum mismatch.")
        # Parsing and checksum verification do not unpickle an untrusted model.
        # Only import archives you generated from this project's notebook.
        backup=root/'imports'/file_sha(archive_path)[:12]
        backup.mkdir(parents=True,exist_ok=True)
        shutil.copy2(archive_path,backup/archive_path.name)
        for directory in ('models','reports'):
            for path in (stage/directory).rglob('*'):
                if path.is_file():
                    relative=path.relative_to(stage)
                    destination=root/relative
                    destination.parent.mkdir(parents=True,exist_ok=True)
                    if destination.exists():
                        previous=backup/'previous'/relative
                        previous.parent.mkdir(parents=True,exist_ok=True)
                        shutil.copy2(destination,previous)
                    shutil.copy2(path,destination)
        return {'profile':profile,'execution_environment':metrics['execution_environment'],
                'selected_model':metrics['selected_model'],'test':metrics['test'],
                'sklearn_version':manifest['sklearn_version'],'backup':str(backup)}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('results_zip',type=Path)
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parent)
    args=parser.parse_args()
    print(json.dumps(import_results(args.results_zip,args.root),indent=2))
