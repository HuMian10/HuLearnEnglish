from kittentts import KittenTTS

model = KittenTTS('checkpoints/kittentts', cache_dir="checkpoints/kittentts")
import time
start = time.time()
audio = model.generate("This high-quality TTS model runs without a GPU.", voice="Jasper")
end = time.time()
print(end - start)

import soundfile as sf
sf.write("output.wav", audio, 24000)