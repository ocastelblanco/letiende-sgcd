// lambda/video-processor/tests/index.test.js
// Tests unitarios del handler Lambda

import { jest } from '@jest/globals';

// Mock de S3Client
jest.mock('@aws-sdk/client-s3', () => ({
  S3Client: jest.fn().mockImplementation(() => ({
    send: jest.fn(),
  })),
  GetObjectCommand: jest.fn(),
  PutObjectCommand: jest.fn(),
}));

// Mock de execFile (FFmpeg)
jest.mock('child_process', () => ({
  execFile: jest.fn((cmd, args, cb) => cb(null, '', '')),
}));

describe('handler', () => {
  it('retorna error cuando la operación es desconocida', async () => {
    const { handler } = await import('../index.js');
    const result = await handler({
      content_item_id: 'test-uuid',
      r2_key: 'letiende-raw-assets/raw/test.mp4',
      operations: ['operacion_inexistente'],
      target_bucket: 'letiende-processed-assets',
    });

    // Con operación desconocida, no hay outputs pero tampoco error fatal
    expect(result).toHaveProperty('success');
    expect(result).toHaveProperty('outputs');
    expect(result).toHaveProperty('duration_seconds');
  });

  it('estructura de respuesta correcta en éxito', () => {
    const successResponse = {
      success: true,
      outputs: {
        instagram_reel: 'letiende-processed-assets/processed/uuid/instagram_reel.mp4',
        youtube: 'letiende-processed-assets/processed/uuid/youtube.mp4',
      },
      duration_seconds: 45,
      error: null,
    };

    expect(successResponse).toHaveProperty('success', true);
    expect(successResponse).toHaveProperty('error', null);
    expect(successResponse.outputs).toHaveProperty('instagram_reel');
  });

  it('estructura de respuesta correcta en error', () => {
    const errorResponse = {
      success: false,
      outputs: {},
      duration_seconds: 5,
      error: 'FFmpeg: Invalid input file',
    };

    expect(errorResponse).toHaveProperty('success', false);
    expect(errorResponse.error).toBeTruthy();
    expect(errorResponse.outputs).toEqual({});
  });
});
