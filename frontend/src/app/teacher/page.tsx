import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { TeacherClient } from "./teacher-client";

/** Server-side auth + role check; the interactive dashboard lives in the client component. */
export default async function TeacherPage() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    redirect("/login");
  }

  const {
    data: { session },
  } = await supabase.auth.getSession();

  const res = session
    ? await fetch(`${process.env.NEXT_PUBLIC_API_URL}/profile/me`, {
        headers: { Authorization: `Bearer ${session.access_token}` },
      }).catch(() => null)
    : null;
  const profile = res?.ok ? await res.json() : null;

  // Defense in depth, not the real boundary -- every /guardian/* endpoint
  // enforces its own authorization regardless of what this page renders.
  // A parent (Decision 034) lands on the same dashboard as a teacher --
  // guardian_links and every /guardian/* query are already generic over
  // how the link was made, so the only thing that differs is copy.
  if (profile?.role !== "teacher" && profile?.role !== "guardian") {
    redirect("/home");
  }

  return <TeacherClient classCode={profile.class_code} viewerRole={profile.role} />;
}
