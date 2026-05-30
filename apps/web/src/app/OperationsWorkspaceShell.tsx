import type { ReactNode } from "react";

import { AppShell } from "@/app/AppShell";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  buildOperationsShellProps,
  type OperationsWorkspaceContext,
} from "@/lib/operations-workspace";

export function OperationsWorkspaceShell({
  activePath,
  children,
  currentPath,
  workspace,
}: {
  activePath: string;
  children: ReactNode;
  currentPath: string;
  workspace: OperationsWorkspaceContext;
}) {
  return (
    <AppShell
      {...buildOperationsShellProps(workspace, {
        activePath,
        currentPath,
      })}
    >
      {children}
    </AppShell>
  );
}

export function OperationalEmptyState({
  body,
  eyebrow,
  title,
}: {
  body: string;
  eyebrow: string;
  title: string;
}) {
  return (
    <Card className="workspace-empty">
      <CardHeader>
        <p className="eyebrow">{eyebrow}</p>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <p>{body}</p>
      </CardContent>
    </Card>
  );
}
