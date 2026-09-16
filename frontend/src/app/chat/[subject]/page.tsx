import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { ChatClient } from "../chat-client";

const VALID_SUBJECTS = ["math", "science"];

/** Server-side auth check and subject validation; the interactive chat UI lives in the client component. */
export default async function SubjectChatPage(props: PageProps<"/chat/[subject]">) {
  const { subject } = await props.params;

  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    redirect("/login");
  }
  if (!VALID_SUBJECTS.includes(subject)) {
    redirect("/home");
  }

  return <ChatClient subject={subject} />;
}
