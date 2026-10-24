import { getUser } from "../db/users.js";
import { listProjects, removeProject } from "../db/projects.js";

export async function getProjects(req) {
  const user = await getUser(req.headers.get("x-user-id") ?? "");
  return Response.json(await listProjects(user.id));
}

export async function deleteProject(req, projectId) {
  const user = getUser(req.headers.get("x-user-id") ?? "");
  if (!user.isAdmin) {
    return new Response("forbidden", { status: 403 });
  }
  await removeProject(projectId);
  return new Response(null, { status: 204 });
}
