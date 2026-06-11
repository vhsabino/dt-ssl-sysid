import os
import subprocess, shutil
from pathlib import Path

def generate_proto_classes():

    INCLUDE = r"C:\Users\victo\Documents\in1144-data-mining-2025-2\libs\protobufs\include\protobufs\pb\proto"
    OUT     = r"C:\Users\victo\Documents\in1144-data-mining-2025-2\proto\generated"
    FILE    = "rc_log.proto"

    # wrapper
    PLUGIN = str((Path.cwd()/".protoc_plugins"/"protoc-gen-python_betterproto.cmd").resolve())

    cmd = [
        shutil.which("protoc") or "protoc",
        f"--plugin=protoc-gen-python_betterproto={PLUGIN}",
        "-I", INCLUDE,                         # adicione mais -I se seus .proto importarem de outras pastas
        f"--python_betterproto_out={OUT}",
        FILE,                                  # relativo ao INCLUDE porque vamos usar cwd=INCLUDE
    ]

    print("CMD:", " ".join(cmd))
    res = subprocess.run(cmd, cwd=INCLUDE, text=True, capture_output=True)
    print("returncode:", res.returncode)
    print("STDOUT:\n", res.stdout)
    print("STDERR:\n", res.stderr)
    if res.returncode != 0:
        # tente novamente com a flag 'optional' para protoc antigo + proto3 optional
        res2 = subprocess.run(cmd + ["--experimental_allow_proto3_optional"], cwd=INCLUDE, text=True, capture_output=True)
        print("\n[retry] returncode:", res2.returncode)
        print("STDOUT:\n", res2.stdout)
        print("STDERR:\n", res2.stderr)
        if res2.returncode != 0:
            raise SystemExit("Falhou mesmo com retry; veja STDERR acima.")
    else:
        print("✅ Sucesso!")