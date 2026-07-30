/** Parse `/skill_name optional message` at line start */
export function parseSlashCommand(text: string): { skill: string | null; message: string } {
  const stripped = text.trim()
  const match = stripped.match(/^\/([a-z][a-z0-9_]{1,63})(?:\s+([\s\S]*))?$/)
  if (!match) return { skill: null, message: text }
  return {
    skill: match[1],
    message: (match[2] ?? '').trim(),
  }
}

export function slashQueryFromInput(text: string): string {
  if (!text.startsWith('/')) return ''
  const after = text.slice(1)
  const space = after.indexOf(' ')
  return (space === -1 ? after : after.slice(0, space)).toLowerCase()
}
