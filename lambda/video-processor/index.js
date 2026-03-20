// lambda/video-processor/index.js
// Handler de AWS Lambda para procesamiento de video con FFmpeg
// Descarga de R2, procesa con FFmpeg, sube resultado a R2

import { S3Client, GetObjectCommand, PutObjectCommand } from '@aws-sdk/client-s3';
import { execFile } from 'child_process';
import { promisify } from 'util';
import { createWriteStream, createReadStream } from 'fs';
import { unlink, mkdir } from 'fs/promises';
import { pipeline } from 'stream/promises';
import { tmpdir } from 'os';
import { join } from 'path';
import { randomUUID } from 'crypto';

const execFileAsync = promisify(execFile);

// Configuración del cliente R2 (compatible con S3)
const r2Client = new S3Client({
  region: 'auto',
  endpoint: process.env.CF_R2_ENDPOINT,
  credentials: {
    accessKeyId: process.env.CF_R2_ACCESS_KEY_ID,
    secretAccessKey: process.env.CF_R2_SECRET_ACCESS_KEY,
  },
});

// Operaciones FFmpeg disponibles
const OPERATIONS = {
  // Reel / TikTok: 9:16, 1080x1920, máx 60s, 50 MB
  resize_9_16: [
    '-vf', 'scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2',
    '-c:v', 'libx264', '-preset', 'fast', '-crf', '23',
    '-c:a', 'aac', '-b:a', '128k', '-t', '60',
  ],
  // YouTube: 16:9, 1920x1080, máx 15min, sin recorte
  compress_youtube: [
    '-vf', 'scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2',
    '-c:v', 'libx264', '-preset', 'medium', '-crf', '20',
    '-c:a', 'aac', '-b:a', '192k',
  ],
  // Instagram Feed: 1:1, 1080x1080, máx 60s
  resize_1_1: [
    '-vf', 'scale=1080:1080:force_original_aspect_ratio=decrease,pad=1080:1080:(ow-iw)/2:(oh-ih)/2',
    '-c:v', 'libx264', '-preset', 'fast', '-crf', '23',
    '-c:a', 'aac', '-b:a', '128k', '-t', '60',
  ],
};

// Mapeo de operación a nombre de plataforma y extensión
const OPERATION_PLATFORM_MAP = {
  resize_9_16: { platform: 'instagram_reel', ext: 'mp4' },
  compress_youtube: { platform: 'youtube', ext: 'mp4' },
  resize_1_1: { platform: 'tiktok', ext: 'mp4' },
};

/**
 * Descarga un objeto de R2 a un archivo temporal
 */
async function downloadFromR2(r2Key, localPath) {
  const [bucket, ...keyParts] = r2Key.split('/');
  const key = keyParts.join('/');

  const response = await r2Client.send(new GetObjectCommand({
    Bucket: bucket,
    Key: key,
  }));

  const writeStream = createWriteStream(localPath);
  await pipeline(response.Body, writeStream);
}

/**
 * Sube un archivo local a R2
 */
async function uploadToR2(localPath, bucket, key, contentType = 'video/mp4') {
  const fileStream = createReadStream(localPath);
  await r2Client.send(new PutObjectCommand({
    Bucket: bucket,
    Key: key,
    Body: fileStream,
    ContentType: contentType,
  }));
}

/**
 * Procesa un video con FFmpeg aplicando la operación indicada
 */
async function processVideo(inputPath, outputPath, operation) {
  const ffmpegArgs = OPERATIONS[operation];
  if (!ffmpegArgs) {
    throw new Error(`Operación desconocida: ${operation}`);
  }

  await execFileAsync('ffmpeg', [
    '-i', inputPath,
    ...ffmpegArgs,
    '-y', // Sobreescribir si existe
    outputPath,
  ]);
}

/**
 * Handler principal de Lambda
 *
 * @param {Object} event
 * @param {string} event.content_item_id - UUID del item en Supabase
 * @param {string} event.r2_key - Key del video en R2 (ej: letiende-raw-assets/raw/uuid.mp4)
 * @param {string[]} event.operations - Lista de operaciones a aplicar
 * @param {string} event.target_bucket - Bucket destino en R2
 */
export const handler = async (event) => {
  const { content_item_id, r2_key, operations, target_bucket } = event;
  const startTime = Date.now();

  // Directorio temporal único para esta ejecución
  const workDir = join(tmpdir(), randomUUID());
  await mkdir(workDir, { recursive: true });

  const inputPath = join(workDir, 'input.mp4');
  const outputs = {};
  const filesToClean = [inputPath];

  try {
    console.log(`Procesando video para content_item_id: ${content_item_id}`);
    console.log(`R2 key origen: ${r2_key}`);
    console.log(`Operaciones: ${operations.join(', ')}`);

    // 1. Descargar video original desde R2
    console.log('Descargando video desde R2...');
    await downloadFromR2(r2_key, inputPath);
    console.log('Video descargado');

    // 2. Aplicar cada operación en paralelo
    await Promise.all(operations.map(async (operation) => {
      const { platform, ext } = OPERATION_PLATFORM_MAP[operation] || {};
      if (!platform) {
        console.warn(`Operación sin mapeo de plataforma: ${operation}`);
        return;
      }

      const outputFileName = `${content_item_id}_${platform}.${ext}`;
      const outputPath = join(workDir, outputFileName);
      filesToClean.push(outputPath);

      console.log(`Procesando: ${operation} → ${outputFileName}`);
      await processVideo(inputPath, outputPath, operation);

      // Subir resultado a R2
      const r2OutputKey = `processed/${content_item_id}/${platform}.${ext}`;
      await uploadToR2(outputPath, target_bucket, r2OutputKey);

      outputs[platform] = `${target_bucket}/${r2OutputKey}`;
      console.log(`✓ ${platform} subido: ${r2OutputKey}`);
    }));

    const durationSeconds = Math.round((Date.now() - startTime) / 1000);

    return {
      success: true,
      outputs,
      duration_seconds: durationSeconds,
      error: null,
    };

  } catch (error) {
    console.error('Error procesando video:', error);
    return {
      success: false,
      outputs: {},
      duration_seconds: Math.round((Date.now() - startTime) / 1000),
      error: error.message,
    };
  } finally {
    // Limpiar archivos temporales
    await Promise.allSettled(filesToClean.map(f => unlink(f).catch(() => {})));
  }
};
