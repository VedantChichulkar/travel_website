import Image from "next/image";

import { MediaImage } from "@/src/components/MediaImage";

export function DestinationImage({ src, name, alt, priority = false, className = "" }: { src: string | null; name: string; alt?: string | null; priority?: boolean; className?: string }) {
  const fallback = <div className={`destination-image-fallback grid h-full w-full place-items-center ${className}`} role="img" aria-label={`No photograph is currently available for ${name}`}><span className="text-6xl font-black text-[var(--brand)]/30" aria-hidden>{name.charAt(0).toUpperCase()}</span></div>;
  if (src?.startsWith("/")) {
    return <Image src={src} alt={`Editorial artwork representing ${name}; not documentary photography`} width={1200} height={800} preload={priority} sizes="(max-width: 640px) 100vw, (max-width: 1024px) 50vw, 33vw" className={`h-full w-full object-cover ${className}`} />;
  }
  return <MediaImage src={src} alt={alt || `Media representing ${name}`} eager={priority} className={`h-full w-full object-cover ${className}`} fallback={fallback} />;
}
