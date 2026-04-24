export function greet(name: string) {
  console.log(name as any)
  return JSON.parse('{"ok": true}')
}
