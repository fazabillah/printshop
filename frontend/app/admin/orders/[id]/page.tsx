export default function OrderDetailPage({ params }: { params: { id: string } }) {
  return (
    <main className="min-h-screen bg-white">
      <div className="container mx-auto px-4 py-12">
        <h1 className="text-4xl font-bold">Order Details</h1>
        <p className="text-gray-600 mt-4">Order ID: {params.id}</p>
      </div>
    </main>
  );
}
