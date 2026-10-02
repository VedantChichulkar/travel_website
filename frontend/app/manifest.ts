import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "Maharashtra Tourist Places",
    short_name: "Tourist Places",
    description: "Discover Maharashtra destinations, active stays, and supported safari experiences.",
    start_url: "/",
    display: "standalone",
    background_color: "#f8fafc",
    theme_color: "#14213d",
    icons: [{ src: "/icon.svg", sizes: "any", type: "image/svg+xml" }],
  };
}
