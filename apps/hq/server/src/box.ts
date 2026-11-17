import fs from 'node:fs/promises';
import { constants } from 'node:fs';
import path from 'node:path';

export const box = {
  async writeFile(file: string, content: string): Promise<void> {
    const dir = path.dirname(file);
    if (await fs.realpath(dir) !== dir) throw new Error('unsafe workspace path');
    const handle = await fs.open(file, constants.O_WRONLY | constants.O_CREAT | constants.O_EXCL | constants.O_NOFOLLOW, 0o600);
    try { await handle.writeFile(content); } finally { await handle.close(); }
  },
};
