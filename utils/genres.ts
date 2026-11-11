interface GenreBook {
  genres?: string | null;
  Genre?: string | null;
  Type?: string | null;
}

const genreGroups: Record<string, string[]> = {
  Literary: ['literary fiction', 'psychological fiction', 'philosophical fiction', 'political fiction', 'coming-of-age'],
  Speculative: ['science fiction', 'dystopian', 'fantasy', 'magical realism', 'mythological fiction', 'horror'],
  Historical: ['historical fiction', 'historical'],
  Romance: ['romance'],
  Contemporary: ['satire', 'essay'],
  'Mystery & Thriller': ['mystery', 'thriller', 'crime'],
  'Non-Fiction': ['memoir', 'biography', 'self-help', 'non-fiction', 'nonfiction'],
};

export const genreColors: Record<string, string> = {
  Literary: '#3b82f6',
  Speculative: '#10b981',
  Historical: '#f59e0b',
  Romance: '#ec4899',
  Contemporary: '#8b5cf6',
  'Mystery & Thriller': '#06b6d4',
  'Non-Fiction': '#ef4444',
  Uncategorized: '#9ca3af',
};

function genreCategory(book: GenreBook): string {
  const genres = (book.genres || book.Genre || '').toLowerCase().split(/[,;/|]/).map(genre => genre.trim());
  const match = Object.entries(genreGroups).find(([, labels]) => genres.some(genre => labels.includes(genre)));
  if (match) return match[0];
  return book.Type?.toLowerCase().replace(/[\s_-]/g, '') === 'nonfiction' ? 'Non-Fiction' : 'Uncategorized';
}

export function getGenreDistribution(booksByYear: Record<string, GenreBook[]>) {
  return Object.entries(booksByYear).map(([year, books]) => {
    const counts = Object.fromEntries(Object.keys(genreColors).map(category => [category, 0]));
    for (const book of books) counts[genreCategory(book)] += 1;
    const percentages = Object.fromEntries(
      Object.entries(counts).map(([category, count]) => [category, count / books.length * 100])
    );
    return { year, ...percentages };
  }).sort((a, b) => Number(a.year) - Number(b.year));
}
