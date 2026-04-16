import subprocess

MODEL_PATH = "/home/ny_san/piper-voices/en_US-lessac-medium.onnx"
PIPER_BIN = "/opt/piper-tts/piper"

def parler(texte):
    subprocess.run(
        f'echo "{texte}" | {PIPER_BIN} -m {MODEL_PATH} -f output.wav --quiet',
        shell=True
    )
    subprocess.run("aplay output.wav", shell=True)