// The demo identities that ship with the seed corpus (mirror of data/users.yaml).
// The picker offers these; the operator pastes a matching token minted with
// `make token SUB=<sub>`. Identity is always carried by the verified token
// (ADR-015) - this list only labels the slots and shows the exact mint command.
export interface DemoIdentity {
  sub: string;
  tenant: string;
  role: string;
  purpose: string;
}

export const DEMO_IDENTITIES: DemoIdentity[] = [
  { sub: "sales@acme", tenant: "acme", role: "sales", purpose: "support" },
  { sub: "legal@acme", tenant: "acme", role: "legal", purpose: "audit" },
  { sub: "admin@acme", tenant: "acme", role: "admin", purpose: "dev" },
  { sub: "support@acme", tenant: "acme", role: "support", purpose: "support" },
  { sub: "user@contoso", tenant: "contoso", role: "sales", purpose: "support" },
];

export function mintCommand(sub: string): string {
  return `make token SUB=${sub}`;
}
