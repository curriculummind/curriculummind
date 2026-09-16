import { redirect } from "next/navigation";

/** The bare /chat route has no subject to show -- send visitors to pick one from /home. */
export default function ChatPage() {
  redirect("/home");
}
