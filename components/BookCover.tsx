import { useEffect, useState } from 'react';

interface BookCoverProps {
  src?: string;
  alt: string;
  author?: string;
  className?: string;
}

export default function BookCover({ src, alt, author = '', className = '' }: BookCoverProps) {
  const fallback = `/api/book-cover?${new URLSearchParams({ title: alt, author, refresh: src ? '1' : '0' })}`;
  const [imageSource, setImageSource] = useState<string | null>(src || fallback);

  useEffect(() => {
    setImageSource(src || fallback);
  }, [src, fallback]);

  return (
    <div className={`relative ${className}`}>
      {imageSource ? (
        <img
          src={imageSource}
          alt={alt}
          className="w-full h-full object-cover"
          loading="eager"
          referrerPolicy="no-referrer"
          onError={() => setImageSource(imageSource === fallback ? null : fallback)}
        />
      ) : (
        <div className="w-full h-full bg-gradient-to-br from-gray-200 to-gray-300 flex items-center justify-center p-4">
          <p className="text-gray-700 text-center font-medium text-sm">{alt}</p>
        </div>
      )}
    </div>
  );
}
