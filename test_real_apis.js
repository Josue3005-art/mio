// Test real API connections
const ccxt = require('ccxt');

async function testRealAPIs() {
    console.log('🔗 Probando conexiones API reales...');
    
    // Configurar Binance
    const binance = new ccxt.binance({
        apiKey: process.env.BINANCE_API_KEY,
        secret: process.env.BINANCE_API_SECRET,
        sandbox: false,
        enableRateLimit: true,
    });
    
    // Configurar KuCoin
    const kucoin = new ccxt.kucoin({
        apiKey: process.env.KUCOIN_API_KEY,
        secret: process.env.KUCOIN_API_SECRET,
        password: process.env.KUCOIN_PASSPHRASE,
        sandbox: false,
        enableRateLimit: true,
    });
    
    const exchanges = [
        { name: 'Binance', client: binance },
        { name: 'KuCoin', client: kucoin }
    ];
    
    for (const exchange of exchanges) {
        try {
            console.log(`\n--- ${exchange.name} ---`);
            
            // Test 1: Verificar balance
            console.log('Verificando balance...');
            const balance = await exchange.client.fetchBalance();
            const totalUSD = Object.entries(balance.total)
                .filter(([asset, amount]) => amount > 0)
                .map(([asset, amount]) => `${asset}: ${amount}`)
                .join(', ');
            
            console.log(`✅ Balance: ${totalUSD || 'Sin fondos'}`);
            
            // Test 2: Precio actual BTC
            console.log('Obteniendo precio BTC/USDT...');
            const ticker = await exchange.client.fetchTicker('BTC/USDT');
            console.log(`✅ BTC/USDT: $${ticker.last}`);
            
            // Test 3: Libro de órdenes
            console.log('Verificando libro de órdenes...');
            const orderBook = await exchange.client.fetchOrderBook('BTC/USDT', 5);
            const spread = ((orderBook.asks[0][0] - orderBook.bids[0][0]) / orderBook.bids[0][0] * 100).toFixed(4);
            console.log(`✅ Spread: ${spread}% (Bid: $${orderBook.bids[0][0]}, Ask: $${orderBook.asks[0][0]})`);
            
        } catch (error) {
            console.log(`❌ Error con ${exchange.name}: ${error.message}`);
        }
    }
    
    // Test de arbitraje real
    console.log('\n🔍 ANÁLISIS DE ARBITRAJE REAL');
    await analyzeRealArbitrage(exchanges);
}

async function analyzeRealArbitrage(exchanges) {
    const symbols = ['BTC/USDT', 'ETH/USDT', 'ADA/USDT'];
    
    for (const symbol of symbols) {
        console.log(`\n--- ${symbol} ---`);
        const prices = {};
        
        // Obtener precios reales
        for (const exchange of exchanges) {
            try {
                const ticker = await exchange.client.fetchTicker(symbol);
                prices[exchange.name] = {
                    bid: ticker.bid,
                    ask: ticker.ask,
                    last: ticker.last
                };
            } catch (error) {
                console.log(`Error obteniendo ${symbol} de ${exchange.name}: ${error.message}`);
            }
        }
        
        // Buscar oportunidades
        const exchangeNames = Object.keys(prices);
        if (exchangeNames.length >= 2) {
            for (let i = 0; i < exchangeNames.length; i++) {
                for (let j = 0; j < exchangeNames.length; j++) {
                    if (i !== j) {
                        const buyExchange = exchangeNames[i];
                        const sellExchange = exchangeNames[j];
                        
                        const buyPrice = prices[buyExchange].ask;
                        const sellPrice = prices[sellExchange].bid;
                        const spread = ((sellPrice - buyPrice) / buyPrice) * 100;
                        
                        if (spread > 0.1) { // Mínimo 0.1%
                            console.log(`📈 ${buyExchange} → ${sellExchange}`);
                            console.log(`   Comprar: $${buyPrice}, Vender: $${sellPrice}`);
                            console.log(`   Spread: ${spread.toFixed(3)}% - Ganancia: $${(30 * spread / 100).toFixed(2)} con $30`);
                        }
                    }
                }
            }
        }
    }
}

// Ejecutar test
testRealAPIs().catch(console.error);