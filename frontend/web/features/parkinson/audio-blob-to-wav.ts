"use client";

type AudioContextConstructor = new (contextOptions?: AudioContextOptions) => AudioContext;

function getAudioContextConstructor(): AudioContextConstructor | null {
  const candidate =
    window.AudioContext ||
    (window as Window & typeof globalThis & { webkitAudioContext?: AudioContextConstructor })
      .webkitAudioContext;

  return candidate ?? null;
}

function mixToMono(audioBuffer: AudioBuffer): Float32Array {
  const { numberOfChannels, length } = audioBuffer;

  if (numberOfChannels <= 1) {
    return audioBuffer.getChannelData(0).slice();
  }

  const mixed = new Float32Array(length);

  for (let channelIndex = 0; channelIndex < numberOfChannels; channelIndex += 1) {
    const channelData = audioBuffer.getChannelData(channelIndex);
    for (let sampleIndex = 0; sampleIndex < length; sampleIndex += 1) {
      mixed[sampleIndex] += channelData[sampleIndex] / numberOfChannels;
    }
  }

  return mixed;
}

function encodeMonoPcm16Wav(samples: Float32Array, sampleRate: number): ArrayBuffer {
  const bytesPerSample = 2;
  const dataSize = samples.length * bytesPerSample;
  const buffer = new ArrayBuffer(44 + dataSize);
  const view = new DataView(buffer);

  const writeString = (offset: number, value: string) => {
    for (let index = 0; index < value.length; index += 1) {
      view.setUint8(offset + index, value.charCodeAt(index));
    }
  };

  writeString(0, "RIFF");
  view.setUint32(4, 36 + dataSize, true);
  writeString(8, "WAVE");
  writeString(12, "fmt ");
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, 1, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * bytesPerSample, true);
  view.setUint16(32, bytesPerSample, true);
  view.setUint16(34, 16, true);
  writeString(36, "data");
  view.setUint32(40, dataSize, true);

  let offset = 44;
  for (let index = 0; index < samples.length; index += 1) {
    const sample = Math.max(-1, Math.min(1, samples[index]));
    const pcm = sample < 0 ? sample * 0x8000 : sample * 0x7fff;
    view.setInt16(offset, Math.round(pcm), true);
    offset += bytesPerSample;
  }

  return buffer;
}

export async function convertAudioBlobToWav(sourceBlob: Blob): Promise<Blob> {
  if (sourceBlob.type === "audio/wav") {
    return sourceBlob;
  }

  const AudioContextCtor = getAudioContextConstructor();
  if (!AudioContextCtor) {
    throw new Error("audio_conversion_not_supported");
  }

  const audioContext = new AudioContextCtor();

  try {
    const sourceBuffer = await sourceBlob.arrayBuffer();
    const audioBuffer = await audioContext.decodeAudioData(sourceBuffer.slice(0));
    const monoSamples = mixToMono(audioBuffer);
    const wavBuffer = encodeMonoPcm16Wav(monoSamples, audioBuffer.sampleRate);
    return new Blob([wavBuffer], { type: "audio/wav" });
  } finally {
    await audioContext.close();
  }
}
