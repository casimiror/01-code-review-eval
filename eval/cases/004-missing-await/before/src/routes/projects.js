import { getUser } from "../db/users.js";
import { listProjects } from "../db/projects.js";

export async function getProjects(req) {
  const user = await getUser(req.headers.get("x-user-id") ?? "");
  return Response.json(await listProjects(user.id));
}
