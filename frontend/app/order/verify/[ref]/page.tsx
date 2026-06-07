export default function VerifyPage({ params }: { params: { ref: string } }) {
  return (
    <main className="min-h-screen bg-white">
      <div className="container mx-auto px-4 py-12">
        <h1 className="text-4xl font-bold">Verify Order</h1>
        <p className="text-gray-600 mt-4">Reference: {params.ref}</p>
      </div>
    </main>
  );
}
