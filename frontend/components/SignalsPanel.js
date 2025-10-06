import { useState, useEffect } from 'react';
import ApiClient from '../utils/api';

export default function SignalsPanel() {
  const [signals, setSignals] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchSignals();
  }, []);

  const fetchSignals = async () => {
    try {
      setLoading(true);
      const data = await ApiClient.getSignals();
      setSignals(data);
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const getSignalColor = (signal) => {
    const normalized = (signal || '').toUpperCase();
    if (normalized === 'BUY') return 'text-green-600 bg-green-100';
    if (normalized === 'SELL') return 'text-red-600 bg-red-100';
    return 'text-gray-600 bg-gray-100';
  };

  const getSignalIcon = (signal) => {
    const normalized = (signal || '').toUpperCase();
    if (normalized === 'BUY') {
      return (
        <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
          <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-8.293l-3-3a1 1 0 00-1.414-1.414L9 5.586 7.707 4.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4a1 1 0 00-1.414-1.414L10 4.414l2.293 2.293a1 1 0 001.414-1.414z" clipRule="evenodd" />
        </svg>
      );
    }
    if (normalized === 'SELL') {
      return (
        <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
          <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
        </svg>
      );
    }
    return (
      <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm-1-11a1 1 0 112 0v2a1 1 0 11-2 0V7zm0 6a1 1 0 112 0 1 1 0 01-2 0z" clipRule="evenodd" />
      </svg>
    );
  };

  const formatValue = (value) => {
    if (value === null || value === undefined) {
      return '---.--';
    }
    if (typeof value === 'number') {
      return value.toFixed(2);
    }
    return value?.toString() || '---.--';
  };

  const formatPrice = (value) => {
    if (value === null || value === undefined) {
      return '$---.--';
    }
    if (typeof value === 'number') {
      return `$${value.toFixed(2)}`;
    }
    return value?.toString() || '$---.--';
  };

  if (loading) {
    return (
      <div className="bg-white overflow-hidden shadow rounded-lg">
        <div className="p-6">
          <div className="animate-pulse space-y-4">
            <div className="h-4 bg-gray-200 rounded w-1/3"></div>
            <div className="space-y-3">
              {[...Array(3)].map((_, i) => (
                <div key={i} className="space-y-2">
                  <div className="h-4 bg-gray-200 rounded w-1/4"></div>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="h-3 bg-gray-200 rounded"></div>
                    <div className="h-3 bg-gray-200 rounded"></div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white overflow-hidden shadow rounded-lg">
        <div className="p-6 text-center">
          <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-red-100 text-red-600">
            <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v3m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <h3 className="text-lg font-medium text-gray-900">Signals are temporarily unavailable</h3>
          <p className="mt-2 text-sm text-gray-600">
            The strategy wasn’t able to publish signal data. Confirm the market-data providers are configured and that
            the trading API is reachable.
          </p>
          <div className="mt-4 flex justify-center space-x-3 text-xs text-gray-500">
            <span>• Validate Tiingo / Alpha Vantage keys</span>
            <span>• Inspect Render bot logs</span>
          </div>
          <button
            onClick={fetchSignals}
            className="mt-6 inline-flex items-center rounded-md border border-transparent bg-primary-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-primary-700"
          >
            Try again
          </button>
          <p className="mt-3 overflow-hidden text-ellipsis whitespace-pre-line break-all rounded bg-red-50 px-3 py-2 text-left text-xs text-red-600">
            {error}
          </p>
        </div>
      </div>
    );
  }

  const signalsData = signals?.signals || {};

  return (
    <div className="bg-white overflow-hidden shadow rounded-lg">
      <div className="p-6">
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-lg leading-6 font-medium text-gray-900">Trading Signals</h3>
          <div className="text-sm text-gray-500">
            Data delayed {signals?.data_delay_minutes || 15} minutes
          </div>
        </div>

        {Object.keys(signalsData).length > 0 ? (
          <div className="space-y-6">
            {Object.entries(signalsData).map(([symbol, data]) => {
              const normalizedSignal = (data.signal || 'HOLD').toUpperCase();
              const signalBadge = (
                <div className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${getSignalColor(normalizedSignal)}`}>
                  {getSignalIcon(normalizedSignal)}
                  <span className="ml-1">{normalizedSignal}</span>
                </div>
              );

              return (
                <div key={symbol} className="border border-gray-200 rounded-lg p-4">
                <div className="flex items-center justify-between mb-4">
                  <h4 className="text-lg font-medium text-gray-900">{symbol}</h4>
                  {data.error ? (
                    <span className="text-red-600 text-sm">Error: {data.error}</span>
                  ) : (
                    signalBadge
                  )}
                </div>

                {!data.error && (
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div>
                      <dt className="text-sm font-medium text-gray-500">SMA 20</dt>
                      <dd className="mt-1 text-sm text-gray-900">
                        {formatValue(data.sma_20)}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-sm font-medium text-gray-500">SMA 50</dt>
                      <dd className="mt-1 text-sm text-gray-900">
                        {formatValue(data.sma_50)}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-sm font-medium text-gray-500">RSI</dt>
                      <dd className="mt-1 text-sm text-gray-900">
                        {formatValue(data.rsi)}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-sm font-medium text-gray-500">Current Price</dt>
                      <dd className="mt-1 text-sm text-gray-900">
                        {formatPrice(data.current_price)}
                      </dd>
                    </div>
                  </div>
                )}

                {!data.error && data.conditions && (
                  <div className="mt-4">
                    <h5 className="text-sm font-medium text-gray-500 mb-2">Signal Conditions</h5>
                    <div className="space-y-1">
                      {Object.entries(data.conditions).map(([condition, met]) => (
                        <div key={condition} className="flex items-center text-sm">
                          <div className={`w-2 h-2 rounded-full mr-2 ${met ? 'bg-green-500' : 'bg-gray-300'}`}></div>
                          <span className={met ? 'text-green-700' : 'text-gray-600'}>
                            {condition.replace(/_/g, ' ').toUpperCase()}: {met ? 'Met' : 'Not Met'}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                </div>
              );
            })}
          </div>
        ) : (
          <div className="text-center py-16 text-sm text-gray-600">
            No live signals are available yet. The strategy publishes updated guidance after the next analysis cycle.
          </div>
        )}

        <div className="mt-6 p-4 bg-blue-50 rounded-lg">
          <h4 className="text-sm font-medium text-blue-900 mb-2">Signal Information</h4>
          <p className="text-sm text-blue-800">
            Signals are <strong>generated by the trading bot during market hours</strong> and stored in the database.
            If no signals appear, the bot hasn't run yet (markets may be closed or the bot is initializing).
            Only signals from the last 15 minutes are displayed to ensure freshness.
          </p>
          <p className="text-sm text-blue-800 mt-2">
            <strong>Strategy:</strong> 20/50-day SMA crossover with RSI filter.
            BUY signals require SMA20 &gt; SMA50 and RSI &lt; 70. SELL signals require SMA20 &lt; SMA50 and RSI &gt; 30.
          </p>
        </div>

        {signals?.timestamp && (
          <div className="mt-4 text-xs text-gray-400">
            Last updated: {new Date(signals.timestamp).toLocaleString()}
          </div>
        )}
      </div>
    </div>
  );
}
