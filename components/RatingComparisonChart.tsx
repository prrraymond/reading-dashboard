import { CartesianGrid, ComposedChart, Legend, ResponsiveContainer, Scatter, Tooltip, XAxis, YAxis } from 'recharts';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';

interface RatedBook {
  Title: string;
  Rating: number;
  'Goodreads Rating': number | null;
}

function ComparisonPlot({ books, print = false }: { books: RatedBook[]; print?: boolean }) {
  const goodreadsBooks = books.filter(book => book['Goodreads Rating'] !== null);
  const height = Math.max(300, books.length * 30 + 100);
  const chart = (
    <ComposedChart
      layout="vertical"
      data={books}
      width={print ? 700 : undefined}
      height={height}
      margin={{ top: 20, right: 20, left: 10, bottom: 20 }}
    >
      <CartesianGrid strokeDasharray="3 3" horizontal={false} />
      <XAxis type="number" domain={[0, 5]} ticks={[0, 1, 2, 3, 4, 5]} orientation="top" />
      <YAxis dataKey="Title" type="category" width={print ? 220 : 300} interval={0} tick={{ fontSize: print ? 11 : 14 }} />
      <Tooltip formatter={value => typeof value === 'number' ? value.toFixed(1) : value} />
      <Legend verticalAlign="top" height={36} />
      <Scatter name="My Rating" dataKey="Rating" fill="#162EA7" r={6} isAnimationActive={false} />
      {goodreadsBooks.length > 0 && (
        <Scatter name="Goodreads Rating" dataKey="Goodreads Rating" data={goodreadsBooks} fill="#94a3b8" r={6} isAnimationActive={false} />
      )}
    </ComposedChart>
  );

  return print ? chart : <ResponsiveContainer width="100%" height={height}>{chart}</ResponsiveContainer>;
}

export default function RatingComparisonChart({ books }: { books: RatedBook[] }) {
  const pages: RatedBook[][] = [];
  for (let index = 0; index < books.length; index += 20) pages.push(books.slice(index, index + 20));

  return (
    <>
      <div className="rating-comparison-screen">
        <Card className="bg-white shadow-sm border-[#e5e7eb] mb-8">
          <CardHeader><CardTitle>Rating Comparisons</CardTitle></CardHeader>
          <CardContent>
            <div className="h-[400px] overflow-y-auto">
              <ComparisonPlot books={books} />
            </div>
          </CardContent>
        </Card>
      </div>
      <div className="rating-comparison-print">
        {pages.map((page, index) => (
          <Card key={index} className="bg-white mb-8">
            <CardHeader><CardTitle>Rating Comparisons{index > 0 && ' (continued)'}</CardTitle></CardHeader>
            <CardContent><ComparisonPlot books={page} print /></CardContent>
          </Card>
        ))}
      </div>
    </>
  );
}
