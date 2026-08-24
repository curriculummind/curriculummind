import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";

/** Sends signed-in students to the chat page, everyone else to login. */
export default async function Home() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  redirect(user ? "/chat" : "/login");
}
