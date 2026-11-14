// Exam Timeline's link to the shared add-on kit (kit/, copied from
// anki-addon-kit): its commands go through the editor's own bridge.

import { call } from "./bridge";
import type { KitCall } from "./kit/types";

export const kitCall: KitCall = <T,>(op: string, args: Record<string, unknown> = {}) => call<T>("kit", { op, ...args });
