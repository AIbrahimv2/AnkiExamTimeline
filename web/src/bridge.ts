// Talks to the add-on's Python side (src/bridge.py).
//
// Inside Anki, `pycmd` appears once the QWebChannel connects, a moment after
// the page loads, so calls wait for it. During development the shim in
// index.html (or tools/devserver.py's page) posts to the dev server instead.

type Pycmd = (arg: string, cb?: (result: unknown) => void) => boolean;

declare global {
  interface Window {
    pycmd?: Pycmd;
    examTimeline?: { reload: () => void };
  }
}

const ready: Promise<Pycmd> = new Promise((resolve) => {
  const check = () => (window.pycmd ? resolve(window.pycmd) : setTimeout(check, 15));
  check();
});

/** Send a command; resolves with the reply, rejects with its error message. */
export async function call<T>(cmd: string, args: Record<string, unknown> = {}): Promise<T> {
  const pycmd = await ready;
  return new Promise((resolve, reject) => {
    pycmd(JSON.stringify({ cmd, ...args }), (raw) => {
      const reply = (raw ?? {}) as T & { error?: string };
      if (reply.error) reject(new Error(reply.error));
      else resolve(reply);
    });
  });
}
