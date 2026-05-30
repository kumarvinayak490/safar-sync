import { redirect } from "next/navigation";

import { currentSession } from "@/lib/auth";
import { rootRedirectFromSession } from "@/lib/auth-routing";

export default async function RootPage() {
  const session = await currentSession();

  redirect(rootRedirectFromSession(session));
}

