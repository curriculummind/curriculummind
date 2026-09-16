import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { ProgressClient } from "./progress-client";

/** Server-side auth check; the interactive progress overview lives in the client component. */
export default async function ProgressPage() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    redirect("/login");
  }

  return <ProgressClient />;
}
