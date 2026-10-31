import { z } from "zod";

export function parseWithSchema<T>(schema: z.ZodType<T>, value: unknown): T {
  return schema.parse(value);
}
