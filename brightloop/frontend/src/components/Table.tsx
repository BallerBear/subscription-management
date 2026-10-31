"use client";
import { motion } from "motion/react";
import type { ReactNode } from "react";
import { cn } from "@/lib/cn";
import { EASE } from "./motion";

export type Column<T> = {
  header: string;
  cell: (row: T) => ReactNode;
  /** numbers, amounts and dates are right-aligned + monospaced */
  numeric?: boolean;
};

export function Table<T extends { id: number | string }>({ columns, rows }: { columns: Column<T>[]; rows: T[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-line text-left text-xs uppercase tracking-wider text-muted">
            {columns.map((c) => (
              <th key={c.header} scope="col" className={cn("px-5 py-3 font-medium", c.numeric && "text-right")}>
                {c.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            // rows slide in one after another; capped so long lists don't drag
            <motion.tr
              key={row.id}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.45, delay: Math.min(i, 12) * 0.04, ease: EASE }}
              className="border-b border-line/70 transition-colors last:border-0 hover:bg-accent-soft/50"
            >
              {columns.map((c) => (
                <td key={c.header} className={cn("px-5 py-3.5", c.numeric && "num text-right")}>
                  {c.cell(row)}
                </td>
              ))}
            </motion.tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
