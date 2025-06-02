import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ComposedChart, Scatter, AreaChart, Area } from 'recharts';
import { BookOpen, Clock, BarChart2 } from 'lucide-react';
import Papa from 'papaparse';
import _ from 'lodash';




interface BookData {
  Title: string;
  Author: string;
  Type: string;
  Genre: string;
  'Year read': number;
  Rating: number;
  Source: string;
  'Goodreads Rating': number;
  'Cover_url': string;
  'num_ratings': number;
  'num_editions': string;
  'genres': string;
  'type': string;
  'Ratings gap': number;
  'Ratings trend': string;
}

interface Stats {
  totalBooks: number;
  avgRating: string;
  currentYear: number;
  lastYear: number;
  currentYearBooks: BookData[];
  yoyGrowth: string;
  typeDistribution: Array<{ name: string; value: number }>;
  fictionProportion: string;
  leadingGenre: string;
  leadingAuthor: string;
  avgGoodreadsRating: number;
  ratingDiff: string;
  isMoreCritical: boolean;
  genreDistribution: Array<{ year: string; [category: string]: string | number; }>;
  yearlyTotals: Array<{ year: string; total: number }>;
  ratingTrends: Array<{
    year: number;
    averageRating: number;
    averageGoodreadsRating: number;
    count: number;
  }>;
  sourcePerformance: Array<{  // Add this
    source: string;
    avgRating: number;
    bookCount: number;
    avgGoodreadsRating: number;
    successRate: number;
  }>;
}

interface CustomTooltipProps {
  active?: boolean;
  payload?: Array<any>;
  label?: string;
}

  const ReadingDashboard = () => {
    
    
    const [bookData, setBookData] = useState<BookData[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
      const loadBookData = async () => {
        try {
          const response = await fetch('/api/book-ratings');
          const jsonData = await response.json(); // Parse JSON directly
          console.log('Fetched book data:', jsonData);

          if (Array.isArray(jsonData)) {
            setBookData(jsonData);
          } else {
            console.warn('Fetched data is not an array:', jsonData);
            setBookData([]);
          }
        } catch (error) {
          console.error('Error loading book data:', error);
          setBookData([]);
        } finally {
          setLoading(false); // Stop the loading spinner regardless of the result
        }
      };

      loadBookData();
    }, []);

    // Handle loading state
    if (loading) {
      return (
        <div className="min-h-screen bg-gray-50 p-8 flex items-center justify-center">
          <p className="text-lg text-gray-600">Loading dashboard...</p>
          {bookData.length > 0 && <p>Data loaded but not rendering...</p>}
        </div>
      );
    }

    // Handle case where no data is available
    if (!bookData.length) {
      return (
        <div className="min-h-screen bg-[#f8fafc] p-8 flex items-center justify-center">
          <p className="text-lg text-[#4b5563]">No data available.</p>
        </div>
      );
    }

  const BookCover = ({ src, alt, className }: { src: string; alt: string; className?: string }) => {
    const [imgSrc, setImgSrc] = useState(src);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(false);

    return (
      <div className={`relative ${className}`}>
        {loading && !error && (
          <div className="absolute inset-0 bg-gray-200 animate-pulse" />
        )}
        {!error ? (
          <img
            src={imgSrc}
            alt={alt}
            className="w-full h-full object-cover"
            loading="lazy"
            onError={() => {
              setError(true);
              setLoading(false);
            }}
            onLoad={() => setLoading(false)}
          />
        ) : (
          <div className="w-full h-full bg-gradient-to-br from-gray-200 to-gray-300 flex items-center justify-center p-4">
            <p className="text-gray-700 text-center font-medium text-sm">{alt}</p>
          </div>
        )}
      </div>
    );
  };


  // Calculate all statistics
  const calculateStats = (data: BookData[]): Stats => {
      // Log the incoming data
    console.log('Data received in calculateStats:', data);

    // Handle invalid data cases
    if (!Array.isArray(data) || data.length === 0) {
      console.warn('Invalid or empty data passed to calculateStats:', data);
      return {
        totalBooks: 0,
        avgRating: '0.0',
        currentYear: new Date().getFullYear(),
        lastYear: new Date().getFullYear() - 1,
        currentYearBooks: [],
        yoyGrowth: '0',
        typeDistribution: [],
        fictionProportion: '0',
        leadingGenre: '',
        leadingAuthor: '',
        avgGoodreadsRating: 0,
        ratingDiff: '0',
        isMoreCritical: false,
        yearlyTotals: [],
        genreDistribution: [],
        ratingTrends: [],
        sourcePerformance: []
      };
    }
    const totalBooks = data.length;
    const avgRating = (data.reduce((acc, curr) => acc + (curr.Rating || 0), 0) / totalBooks).toFixed(1);

    // Year-based calculations
    const booksByYear = _.groupBy(data, 'Year read');
    const years = Object.keys(booksByYear).map(Number).sort((a, b) => b - a);
    const currentYear = years[0];
    const lastYear = years[1];
    const currentYearBooks = booksByYear[currentYear] || [];
    const lastYearBooks = booksByYear[lastYear] || [];
    

    // Simple YoY calculation based on total books
    const yoyGrowth = ((currentYearBooks.length / lastYearBooks.length - 1) * 100).toFixed(0);

    // Type distribution
    const typeDistribution = _.map(
      _.groupBy(data, 'Type'),
      (books, type) => ({
        name: type || 'Uncategorized',
        value: (books.length / totalBooks) * 100
      })
    );

    // Fiction proportion
    const fictionProportion = (typeDistribution.find(t => t.name === 'Fiction')?.value.toFixed(0) || '0');

    // Genre stats
    const genreCounts: Record<string, number> = {};
    data.forEach(book => {
      // if (book.Genre) {
      //   genreCounts[book.Genre] = (genreCounts[book.Genre] || 0) + 1;
      // }
      if (book.genres) {
        const g = book.genres.trim().toLowerCase();
        genreCounts[g] = (genreCounts[g] || 0) + 1;
      }
    });
    const leadingGenre = Object.entries(genreCounts)
      .sort(([,a], [,b]) => b - a)[0]?.[0] || '';

    // Author stats
    const authorCounts: Record<string, number> = {};
    data.forEach(book => {
      if (book.Author) {
        authorCounts[book.Author] = (authorCounts[book.Author] || 0) + 1;
      }
    });
    const leadingAuthor = Object.entries(authorCounts)
      .sort(([,a], [,b]) => b - a)[0]?.[0] || '';

    // Goodreads comparison
    const avgGoodreadsRating = data.reduce((acc, curr) => acc + (curr['Goodreads Rating'] || 0), 0) / totalBooks;
    const ratingDiff = (Number(avgRating) - avgGoodreadsRating).toFixed(1);
    const isMoreCritical = Number(ratingDiff) < 0;

    // Calculate rating trends by year
    const ratingTrends = Object.entries(booksByYear).map(([year, books]) => {
      const bookArray = books as BookData[]; // Explicitly cast books to BookData[]
      return {
        year: Number(year),
        averageRating: bookArray.reduce((sum, book) => sum + (book.Rating || 0), 0) / bookArray.length,
        averageGoodreadsRating: bookArray.reduce((sum, book) => sum + (book['Goodreads Rating'] || 0), 0) / bookArray.length,
        count: bookArray.length,
      };
    }).sort((a, b) => a.year - b.year);
    

    // Create yearly totals time series
    // const yearlyTotals = years.map(year => ({
    //   year: year.toString(),
    //   total: booksByYear[year].length
    // })).sort((a, b) => Number(a.year) - Number(b.year));
    const yearlyTotals = [...data]
      .reduce((acc, book) => {
      const year = book['Year read'].toString();
      acc[year] = (acc[year] || 0) + 1;
      return acc;
      }, {} as Record<string, number>);

    const yearlyData = Object.entries(yearlyTotals)
      .map(([year, total]) => ({
        year,
        total
      }))
      .sort((a, b) => Number(a.year) - Number(b.year));

    const genreCategories = {
        'Literary': ['literary fiction', 'psychological fiction', 'philosophical fiction', 'political fiction'],
        'Speculative': ['science fiction', 'dystopian', 'fantasy', 'magical realism', 'mythological fiction'],
        'Historical': ['historical fiction'],
        'Romance': ['romance'],
        'Contemporary': ['satire', 'essay'],
        'Non-Fiction': ['memoir', 'self-help', 'non-fiction', 'nonfiction']
      };
       
       // In calculateStats:

    const genreByYear = _.chain(data)
    .groupBy('Year read')
    .map((books, year) => {
      const result = { year: year.toString() };
      
      // Calculate genres for each category
      Object.keys(genreCategories).forEach(category => {
        const matchingBooks = books.filter(book => 
          genreCategories[category].includes(book.genres.trim().toLowerCase())
        );
        result[category] = Number((matchingBooks.length / books.length * 100).toFixed(2));
      });
      
      // Calculate total categorized percentage
      const categorizedPercentage = Object.keys(result)
        .filter(key => key !== 'year')
        .reduce((sum, key) => sum + (result[key] || 0), 0);
      
      // Add uncategorized percentage to make total 100%
      result['Uncategorized'] = Number((100 - categorizedPercentage).toFixed(2));
      
      return result;
    })
    .sortBy('year')
    .value();
    const sourceStats = _.chain(data)
    .filter(book => book.Source && book.Source.trim() !== '') // Filter out empty sources
    .groupBy('Source')
    .map((books, source) => {
      const avgRating = books.reduce((sum, book) => sum + (book.Rating || 0), 0) / books.length;
      const avgGoodreadsRating = books.reduce((sum, book) => sum + (book['Goodreads Rating'] || 0), 0) / books.length;
      const booksAbove4 = books.filter(book => book.Rating >= 4).length;
      const successRate = (booksAbove4 / books.length) * 100;
      
      return {
        source: source,
        avgRating: Number(avgRating.toFixed(2)),
        bookCount: books.length,
        avgGoodreadsRating: Number(avgGoodreadsRating.toFixed(2)),
        successRate: Number(successRate.toFixed(1))
      };
    })
    .orderBy(['avgRating'], ['desc'])
    .value();
    // const genreByYear = _.chain(data)
    //    .groupBy('Year read')
    //    .map((books, year) => {
    //      const result = { year: year.toString() };
         
    //      Object.keys(genreCategories).forEach(category => {
    //        const matchingBooks = books.filter(book => 
    //          genreCategories[category].some(genre => 
    //            book.genres?.toLowerCase() === genre
    //          )
    //        );
    //        // Calculate percentage based on actual matches
    //        result[category] = Math.round((matchingBooks.length / books.length) * 100);
    //      });
         
    //      // Ensure total adds up to 100%
    //      const total = Object.values(result)
    //                        .filter(v => typeof v === 'number')
    //                        .reduce((a, b) => a + b, 0);
         
    //      if (total < 100) {
    //        result['Uncategorized'] = 100 - total;
    //      }
         
    //      return result;
    //    })
    //    .sortBy('year')
    //    .value();

    // Add console.log before chart:
    // console.log('Chart data:', stats.yearlyTotals);
    // console.log('Final yearlyData:', yearlyData);
    // console.log('Books data:', data.map(b => b.Genre));
    // console.log('Genre by year:', genreByYear);
    // console.log('Sample book genres:', data.slice(0, 5).map(b => ({
    //   year: b['Year read'],
    //   genres: b.genres
    // })));
    // console.log('Unique genres:', _.uniq(data.map(b => b.genres)));
    // Add this right after the stats calculation


    return {
      totalBooks,
      avgRating,
      currentYear,
      lastYear,
      currentYearBooks,
      yoyGrowth,
      typeDistribution,
      fictionProportion,
      leadingGenre,
      leadingAuthor,
      avgGoodreadsRating,
      ratingDiff,
      isMoreCritical,
      yearlyTotals: yearlyData,
      genreDistribution: genreByYear,
      ratingTrends,
      sourcePerformance: sourceStats
    };
  };

  const stats = calculateStats(bookData);

  console.log('Book data sample:', bookData.slice(0, 3));
  console.log('Source values:', bookData.map(book => book.Source));
  console.log('Unique sources:', Array.from(new Set(bookData.map(book => book.Source))));
  console.log('Source performance:', stats.sourcePerformance);
  // In your API endpoint, add logging:
  console.log('Sample database row:', rows[0]); // Log first row to see column names
  console.log('All column names:', Object.keys(rows[0] || {}));

// Sort books by Goodreads Rating (desc) and then Title (asc)
  const sortedBooks = [...bookData]
    .sort((a, b) => {
      // First sort by Goodreads Rating (descending)
      const goodreadsRatingDiff = (b['Goodreads Rating'] || 0) - (a['Goodreads Rating'] || 0);
      // If Goodreads ratings are equal, sort by Title (ascending)
      return goodreadsRatingDiff !== 0 ? goodreadsRatingDiff : a.Title.localeCompare(b.Title);
    })
    .map(book => ({
      ...book,
      Rating: book.Rating || 0,
      'Goodreads Rating': book['Goodreads Rating'] || 0
    }));

  const CustomTooltip = ({ active, payload, label }: CustomTooltipProps) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-white p-4 border border-gray-200 rounded-lg shadow-sm">
          <p className="text-sm font-medium mb-2">{label}</p>
          {payload.map((entry, index) => (
            <p key={index} className="text-sm" style={{ color: entry.color }}>
              {entry.name}: {typeof entry.value === 'number' ? entry.value.toFixed(1) : entry.value}
            </p>
          ))}
        </div>
      );
    }
    return null;
  };

  const BooksTooltip = ({ active, payload, label }: CustomTooltipProps) => {
    if (active && payload && payload.length) {
      // Find books for this year
      const year = Number(label);
      const booksFromYear = bookData.filter(book => book['Year read'] === year);
      
      // Calculate dynamic max height based on number of books
      // Base height for header + some padding
      const baseHeight = 60;
      // Height per book row (adjust as needed)
      const rowHeight = 30;
      // Calculate total needed height with some buffer
      const neededHeight = baseHeight + (booksFromYear.length * rowHeight);
      // Get viewport height
      const viewportHeight = typeof window !== 'undefined' ? window.innerHeight : 800;
      // Max height should be at most 80% of viewport height
      const maxHeight = Math.min(neededHeight, viewportHeight * 0.8);
      
      return (
        <div className="bg-white p-4 border border-gray-200 rounded-lg shadow-sm max-w-xs"
             style={{ maxHeight: `${maxHeight}px`, overflow: 'auto' }}>
          <p className="text-sm font-medium mb-2 sticky top-0 bg-white pb-2 border-b">
            {year}: {payload[0].value} books
          </p>
          
          {booksFromYear.length > 0 ? (
            <div>
              <table className="w-full text-xs">
                <thead className="sticky top-8 bg-white">
                  <tr>
                    <th className="text-left py-1">Title</th>
                    <th className="text-right py-1">Rating</th>
                  </tr>
                </thead>
                <tbody>
                  {booksFromYear
                    .sort((a, b) => b.Rating - a.Rating) // Sort by rating (highest first)
                    .map((book, index) => (
                      <tr key={index} className="border-t border-gray-100">
                        <td className="py-1 pr-2">{book.Title}</td>
                        <td className="py-1 text-right font-medium">
                          {book.Rating?.toFixed(1) || '-'} ★
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="text-xs text-gray-500">No book details available</p>
          )}
        </div>
      );
    }
    return null;
  };

  return (
    <div className="min-h-screen bg-[#f8fafc] p-8 font-book">
      <div className="max-w-7xl mx-auto">
        <h1 className="text-4xl font-bold text-[#1a4480] mb-8">Reading Activity Dashboard</h1>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6" style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)' }}>
          <div className="p-4">
            <Card className="bg-white shadow-sm border-[#e5e7eb] hover:shadow-md transition-shadow duration-200">
              <div className="flex items-center">
                <BookOpen className="h-8 w-8 text-blue-600" />
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-500">Total Books Finished</p>
                  <h3 className="text-lg font-bold text-blue-900">{stats.totalBooks}</h3>
                </div>
              </div>
            </Card>
          </div>

          <div className="p-4">
            <Card className="bg-white shadow-sm border-[#e5e7eb] hover:shadow-md transition-shadow duration-200">
              <div className="flex items-center">
                <Clock className="h-8 w-8 text-blue-600" />
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-500">Books This Year</p>
                  <h3 className="text-lg font-bold text-blue-900">
                    {stats.currentYearBooks.length}
                    <span className={`text-sm font-normal ml-2 ${Number(stats.yoyGrowth) >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                      {Number(stats.yoyGrowth) >= 0 ? '↑' : '↓'} {Math.abs(Number(stats.yoyGrowth))}% YoY
                    </span>
                  </h3>
                </div>
              </div>
            </Card>
          </div>

          <div className="p-4">
            <Card className="bg-white shadow-sm border-[#e5e7eb] hover:shadow-md transition-shadow duration-200">
              <div className="flex items-center">
                <BarChart2 className="h-8 w-8 text-blue-600" />
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-500">Average Ratings (compared to Goodreads)</p>
                  <h3 className="text-lg font-bold text-blue-900">
                    <span className="text-blue-600">{stats.avgRating}</span>
                    <span className="mx-2">/</span>
                    <span className="text-gray-500">{stats.avgGoodreadsRating.toFixed(1)}</span>
                    <span className="text-sm font-normal text-gray-500 ml-2">
                      ({stats.isMoreCritical ? 'more critical' : 'more generous'})
                    </span>
                  </h3>
                </div>
              </div>
            </Card>
          </div>
        </div>
        {/* <div className="grid grid-cols-1 lg:grid-cols-3 gap-6" style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)' }}>
          <div className="p-4">
            <Card className="metric-card hover:shadow-md transition-shadow duration-200">
              <CardContent className="pt-6">
                <div className="flex items-center">
                  <BookOpen className="h-8 w-8 text-[#162EA7]" />
                  <div className="ml-4">
                    <p className="text-sm font-medium text-[#4b5563]">Total Books Read</p>
                    <h3 className="text-2xl font-bold text-[#1e293b]">{stats.totalBooks}</h3>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          <div className="p-4">
            <Card className="metric-card hover:shadow-md transition-shadow duration-200">
              <CardContent className="pt-6">
                <div className="flex items-center">
                  <Clock className="h-8 w-8 text-[#162EA7]" />
                  <div className="ml-4">
                    <p className="text-sm font-medium text-[#4b5563]">Books This Year</p>
                    <h3 className="text-2xl font-bold text-[#1e293b]">
                      {stats.currentYearBooks.length}
                      <span className="text-sm font-normal ml-2 text-[#dc2626]">
                        ↓ {Math.abs(Number(stats.yoyGrowth))}% YoY
                      </span>
                    </h3>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          <div className="p-4">
            <Card className="metric-card hover:shadow-md transition-shadow duration-200">
              <CardContent className="pt-6">
                <div className="flex items-center">
                  <BarChart2 className="h-8 w-8 text-[#162EA7]" />
                  <div className="ml-4">
                    <p className="text-sm font-medium text-[#4b5563]">Average Ratings</p>
                    <h3 className="text-2xl font-bold text-[#1e293b]">
                      <span className="text-[#162EA7]">{stats.avgRating}</span>
                      <span className="mx-2">/</span>
                      <span className="text-[#64748b]">{stats.avgGoodreadsRating.toFixed(1)}</span>
                      <span className="text-sm font-normal text-[#64748b] ml-2">
                        ({stats.isMoreCritical ? 'more critical' : 'more generous'})
                      </span>
                    </h3>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </div> */}

        {/* Executive Summary */}
        {/* <Card className="bg-white shadow-sm border-[#e5e7eb] hover:shadow-md transition-shadow duration-200 mb-8"> */}
        <Card className="bg-gray-100 text-[#0f172a] shadow-sm border-[#e5e7eb] hover:shadow-md transition-shadow duration-200 mb-8">
          <CardHeader className="bg-gray-100">
            <CardTitle className="text-[#0f172a]">Executive Summary</CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-3">
              <li className="flex items-start">
                <span className="text-blue-500 mr-2">•</span>
                <span>
                  Finished {stats.currentYearBooks.length} books so far in {stats.currentYear}, a {stats.yoyGrowth}% change from {stats.lastYear}.
                </span>
              </li>
              <li className="flex items-start">
                <span className="text-blue-500 mr-2">•</span>
                <span>
                  Average rating for books was {stats.avgRating}, compared to {stats.avgGoodreadsRating.toFixed(1)} average rating for the same set on Goodreads.
                </span>
              </li>
              <li className="flex items-start">
                <span className="text-blue-500 mr-2">•</span>
                <span>
                  {stats.fictionProportion}% of total books finished were fiction, and {stats.leadingGenre} is the genre most read among finished books.
                </span>
              </li>
              <li className="flex items-start">
                <span className="text-blue-500 mr-2">•</span>
                <span>
                  {stats.leadingAuthor} is author most read, overall.
                </span>
              </li>
            </ul>
          </CardContent>
        </Card>




        <div>
          <Card className="bg-white shadow-sm border-[#e5e7eb] hover:shadow-md transition-shadow duration-200 mb-8">
            <CardHeader>
              <CardTitle className="text-[#1a4480]">Books Finished by Year</CardTitle>
            </CardHeader>
            <CardContent>
              <div style={{ height: '400px', width: '100%' }}>
                <ResponsiveContainer>
                  <BarChart
                    data={stats.yearlyTotals}
                    margin={{ top: 20, right: 30, left: 20, bottom: 20 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                    <XAxis 
                      dataKey="year" 
                      tick={{ fill: '#4b5563' }}
                    />
                    <YAxis 
                      tick={{ fill: '#4b5563' }}
                      domain={[0, 'auto']}
                    />
                    <Tooltip 
                      content={BooksTooltip}
                      wrapperStyle={{ zIndex: 1000 }}
                    />
                    <Bar 
                      dataKey="total" 
                      fill="#162EA7"
                      radius={[4, 4, 0, 0]}
                      name="Books Read"
                    />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>
        </div>


        {/* Genre Distribution Over Time */}
{/* Genre Distribution Over Time - Improved Colors */}
        <Card className="bg-white shadow-sm border-[#e5e7eb] hover:shadow-md transition-shadow duration-200 mb-8">
          <CardHeader>
            <CardTitle className="text-[#1a4480]">Genre Distribution Over Time</CardTitle>
          </CardHeader>
          <CardContent>
            <div style={{ height: '400px', width: '100%' }}>
              <ResponsiveContainer>
                <AreaChart
                  data={stats.genreDistribution}
                  margin={{ top: 20, right: 30, left: 20, bottom: 20 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                  <XAxis dataKey="year" tick={{ fill: '#4b5563' }} />
                  <YAxis 
                    tickFormatter={(value) => `${value}%`} 
                    tick={{ fill: '#4b5563' }} 
                    domain={[0, 100]} 
                  />
                  <Tooltip
                    formatter={(value) => {
                      if (typeof value === 'number') {
                        return `${value.toFixed(1)}%`;
                      }
                      return `${value}%`;
                    }}
                    contentStyle={{ backgroundColor: '#fff', borderRadius: '4px', boxShadow: '0 2px 8px rgba(0,0,0,0.15)', border: '1px solid #e5e7eb' }}
                    itemStyle={{ padding: '4px 0' }}
                  />
                  <Legend 
                    verticalAlign="bottom" 
                    height={36} 
                    iconType="circle"
                    iconSize={10}
                    wrapperStyle={{ paddingTop: '10px' }}
                  />
                  {/* Using a more visually distinct and harmonious color palette */}
                  <Area type="monotone" dataKey="Literary" stackId="1" stroke="#3b82f6" fill="#3b82f6" fillOpacity={0.9} />
                  <Area type="monotone" dataKey="Speculative" stackId="1" stroke="#10b981" fill="#10b981" fillOpacity={0.9} />
                  <Area type="monotone" dataKey="Historical" stackId="1" stroke="#f59e0b" fill="#f59e0b" fillOpacity={0.9} />
                  <Area type="monotone" dataKey="Romance" stackId="1" stroke="#ec4899" fill="#ec4899" fillOpacity={0.9} />
                  <Area type="monotone" dataKey="Contemporary" stackId="1" stroke="#8b5cf6" fill="#8b5cf6" fillOpacity={0.9} />
                  <Area type="monotone" dataKey="Non-Fiction" stackId="1" stroke="#ef4444" fill="#ef4444" fillOpacity={0.9} />
                  <Area type="monotone" dataKey="Uncategorized" stackId="1" stroke="#9ca3af" fill="#9ca3af" fillOpacity={0.7} />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        {/* Best Rated Books - Improved Image Handling */}
        <Card className="bg-white shadow-sm border-[#e5e7eb] hover:shadow-md transition-shadow duration-200 mb-8">
          <CardHeader>
            <CardTitle className="text-[#1a4480]">My Best</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-row gap-5 overflow-x-auto pb-8">
              {bookData
                .filter(book => book.Rating >= 4.5)
                .sort((a, b) => b.Rating - a.Rating)
                .slice(0, 8)
                .map((book, index) => (
                  <div 
                    key={index} 
                    className="flex-shrink-0 w-40 group relative"
                  >
                    <div className="relative overflow-hidden rounded-md shadow-md hover:shadow-lg transition-all duration-200">
                      <img
                        src={book.Cover_url || '/placeholder-book-cover.jpg'}
                        alt={book.Title}
                        className="w-full h-56 object-cover bg-gray-50"
                        style={{ 
                          // imageRendering: 'high-quality',
                          WebkitBackfaceVisibility: 'hidden',
                          transform: 'translateZ(0)',
                        }}
                        loading="lazy"
                        onError={(e) => {
                          e.currentTarget.src = '/placeholder-book-cover.jpg';
                        }}
                      />
                    </div>
                    <div className="mt-3 space-y-2">
                      <div className="text-sm font-medium text-[#4b5563] line-clamp-2">
                        {book.Title}
                      </div>
                      <div className="text-xs text-gray-500">
                        {book.Author}
                      </div>
                      <div className="inline-flex items-center justify-center px-2.5 py-1 rounded-full text-sm bg-[#162EA7] text-white">
                        {book.Rating.toFixed(1)} ★
                      </div>
                    </div>
                  </div>
                ))}
            </div>
          </CardContent>
        </Card>

        {/* Rating Comparison Chart */}
        <Card className="bg-white shadow-sm border-[#e5e7eb] hover:shadow-md transition-shadow duration-200 mb-8">
            <CardHeader>
              <CardTitle className="text-[#1a4480]">Rating Comparisons</CardTitle>
            </CardHeader>
            <CardContent className="pl-0">
              <div className="h-[400px] overflow-y-auto">
                <ResponsiveContainer width="100%" height={1600}>
                  <ComposedChart
                    layout="vertical"
                    data={sortedBooks}
                    margin={{ top: 20, right: 30, left: 100, bottom: 20 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                    <XAxis 
                      type="number" 
                      domain={[0, 5]} 
                      ticks={[0, 1, 2, 3, 4, 5]}
                      tick={{ fontSize: 14 }} // Increase font size
                      tickFormatter={(value) => typeof value === 'number' ? value.toFixed(1) : value}
                      orientation = "top"                    
                    />
                    <YAxis 
                      dataKey="Title" 
                      type="category"
                      width={300}
                      tick={{ 
                        fontSize: 14,
                        textAnchor: 'end', // Align labels to the left
                        dx: -10, // Shift labels to the left for alignment
                        // dy: 30,
                      }}
                      interval={0}
                    />
                    <Tooltip 
                      content={<CustomTooltip />}
                    />
                    <Legend 
                      verticalAlign="top" 
                      height={36}
                    />
                    <Scatter 
                      name="My Rating" 
                      dataKey="Rating" 
                      fill="#162EA7"
                      r={6}
                    />
                    <Scatter 
                      name="GoodReads Rating" 
                      dataKey="Goodreads Rating" 
                      fill="#94a3b8"
                      r={6}
                    />
                  </ComposedChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>

{/* Rating Trends Chart - Fixed Version */}
{/* Rating Trends Chart - Simplified with Enhanced Tooltip */}
        <Card className="bg-white shadow-sm border-[#e5e7eb] hover:shadow-md transition-shadow duration-200 mb-8">
          <CardHeader>
            <CardTitle className="text-[#1a4480]">Rating Trends Over Time</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-80">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart
                  data={stats.ratingTrends}
                  margin={{ top: 20, right: 30, left: 20, bottom: 20 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                  <XAxis 
                    dataKey="year" 
                    tick={{ fill: '#4b5563' }}
                  />
                  <YAxis 
                    domain={[0, 5]} 
                    ticks={[0, 1, 2, 3, 4, 5]}
                    tick={{ fill: '#4b5563' }}
                    label={{ value: 'Rating (0-5)', angle: -90, position: 'insideLeft', style: { textAnchor: 'middle', fill: '#4b5563' } }}
                  />
                  <Tooltip
                    content={({ active, payload, label }) => {
                      if (active && payload && payload.length) {
                        return (
                          <div className="bg-white p-4 border border-gray-200 rounded-lg shadow-sm">
                            <p className="text-sm font-medium mb-2">{label}</p>
                            <div className="space-y-1">
                              <p className="text-sm text-[#162EA7]">
                                My Rating: {typeof payload[0].value === 'number' ? payload[0].value.toFixed(2) : payload[0].value}
                              </p>
                              <p className="text-sm text-[#94a3b8]">
                                Goodreads: {typeof payload[1].value === 'number' ? payload[1].value.toFixed(2) : payload[1].value}
                              </p>
                              <div className="mt-2 pt-2 border-t border-gray-100">
                                <p className="text-sm font-medium text-[#16a34a]">
                                  Books Read: {payload[0].payload.count}
                                </p>
                              </div>
                            </div>
                          </div>
                        );
                      }
                      return null;
                    }}
                  />
                  <Legend verticalAlign="top" height={36} />
                  <Line
                    name="My Average Rating"
                    type="monotone"
                    dataKey="averageRating"
                    stroke="#162EA7"
                    strokeWidth={2}
                    dot={{ r: 4, fill: "#162EA7" }}
                    activeDot={{ r: 8 }}
                  />
                  <Line
                    name="Goodreads Average"
                    type="monotone"
                    dataKey="averageGoodreadsRating"
                    stroke="#94a3b8"
                    strokeWidth={2}
                    dot={{ r: 4, fill: "#94a3b8" }}
                    activeDot={{ r: 8 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        {/* Source Performance Analysis */}
        <Card className="bg-white shadow-sm border-[#e5e7eb] hover:shadow-md transition-shadow duration-200 mb-8">
          <CardHeader>
            <CardTitle className="text-[#1a4480]">Average Ratings by Source</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
              {/* Bar Chart */}
              <div style={{ height: '300px', width: '100%' }}>
                <ResponsiveContainer>
                  <BarChart
                    data={stats.sourcePerformance}
                    margin={{ top: 20, right: 30, left: 20, bottom: 60 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                    <XAxis 
                      dataKey="source" 
                      tick={{ fill: '#4b5563', fontSize: 12 }}
                      angle={-45}
                      textAnchor="end"
                      height={80}
                    />
                    <YAxis 
                      tick={{ fill: '#4b5563' }}
                      domain={[0, 5]}
                      label={{ value: 'Average Rating', angle: -90, position: 'insideLeft' }}
                    />
                    <Tooltip 
                      content={({ active, payload, label }) => {
                        if (active && payload && payload.length) {
                          const data = payload[0].payload;
                          return (
                            <div className="bg-white p-4 border border-gray-200 rounded-lg shadow-sm">
                              <p className="text-sm font-medium mb-2">{label}</p>
                              <p className="text-sm text-[#162EA7]">
                                Avg Rating: {data.avgRating}★
                              </p>
                              <p className="text-sm text-[#94a3b8]">
                                Goodreads Avg: {data.avgGoodreadsRating}★
                              </p>
                              <p className="text-sm text-[#16a34a]">
                                Books: {data.bookCount}
                              </p>
                              <p className="text-sm text-[#dc2626]">
                                Success Rate: {data.successRate}% (4+ stars)
                              </p>
                            </div>
                          );
                        }
                        return null;
                      }}
                    />
                    <Bar 
                      dataKey="avgRating" 
                      fill="#162EA7"
                      radius={[4, 4, 0, 0]}
                      name="Average Rating"
                    />
                  </BarChart>
                </ResponsiveContainer>
              </div>

              {/* Source Performance Table */}
              <div className="overflow-hidden">
                <h3 className="text-lg font-semibold text-[#1a4480] mb-4">Source Performance Summary</h3>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="text-left py-3 px-4 font-medium text-gray-700">Source</th>
                        <th className="text-right py-3 px-4 font-medium text-gray-700">Avg Rating</th>
                        <th className="text-right py-3 px-4 font-medium text-gray-700">Books</th>
                        <th className="text-right py-3 px-4 font-medium text-gray-700">Success Rate</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-200">
                      {stats.sourcePerformance.map((source, index) => (
                        <tr key={index} className="hover:bg-gray-50">
                          <td className="py-3 px-4 font-medium text-gray-900">{source.source}</td>
                          <td className="py-3 px-4 text-right">
                            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                              {source.avgRating}★
                            </span>
                          </td>
                          <td className="py-3 px-4 text-right text-gray-600">{source.bookCount}</td>
                          <td className="py-3 px-4 text-right">
                            <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                              source.successRate >= 70 ? 'bg-green-100 text-green-800' :
                              source.successRate >= 50 ? 'bg-yellow-100 text-yellow-800' :
                              'bg-red-100 text-red-800'
                            }`}>
                              {source.successRate}%
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default ReadingDashboard;