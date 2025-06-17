// Test CCXT functionality
const ccxt = require('ccxt');

async function testCCXT() {
    console.log('Probando CCXT con múltiples exchanges...');
    
    const exchanges = ['binance', 'kucoin', 'okx', 'bybit'];
    
    for (const exchangeName of exchanges) {
        try {
            console.log(`\n--- Probando ${exchangeName.toUpperCase()} ---`);
            
            const exchange = new ccxt[exchangeName]({
                sandbox: true,
                enableRateLimit: true,
            });
            
            // Test 1: Obtener mercados
            console.log('Obteniendo mercados...');
            const markets = await exchange.loadMarkets();
            const marketCount = Object.keys(markets).length;
            console.log(`✅ ${marketCount} mercados disponibles`);
            
            // Test 2: Obtener ticker
            console.log('Obteniendo precio BTC/USDT...');
            const ticker = await exchange.fetchTicker('BTC/USDT');
            console.log(`✅ BTC/USDT: $${ticker.last} (Bid: $${ticker.bid}, Ask: $${ticker.ask})`);
            
            // Test 3: Obtener libro de órdenes
            console.log('Obteniendo libro de órdenes...');
            const orderBook = await exchange.fetchOrderBook('BTC/USDT', 5);
            console.log(`✅ Libro: ${orderBook.bids.length} bids, ${orderBook.asks.length} asks`);
            console.log(`   Mejor bid: $${orderBook.bids[0][0]}, Mejor ask: $${orderBook.asks[0][0]}`);
            
        } catch (error) {
            console.log(`❌ Error con ${exchangeName}: ${error.message}`);
        }
    }
    
    // Test de arbitraje
    console.log('\n--- ANÁLISIS DE ARBITRAJE ---');
    await testArbitrage();
}

async function testArbitrage() {
    const exchanges = ['binance', 'kucoin', 'okx'];
    const symbol = 'BTC/USDT';
    const prices = {};
    
    // Obtener precios
    for (const exchangeName of exchanges) {
        try {
            const exchange = new ccxt[exchangeName]({
                sandbox: true,
                enableRateLimit: true,
            });
            
            const ticker = await exchange.fetchTicker(symbol);
            prices[exchangeName] = {
                bid: ticker.bid,
                ask: ticker.ask,
                last: ticker.last
            };
        } catch (error) {
            console.log(`Error obteniendo precio de ${exchangeName}: ${error.message}`);
        }
    }
    
    // Buscar oportunidades
    console.log('\nOportunidades de arbitraje detectadas:');
    let opportunityFound = false;
    
    for (const buyExchange in prices) {
        for (const sellExchange in prices) {
            if (buyExchange !== sellExchange) {
                const buyPrice = prices[buyExchange].ask;
                const sellPrice = prices[sellExchange].bid;
                const spread = ((sellPrice - buyPrice) / buyPrice) * 100;
                
                if (spread > 0.1) { // Mínimo 0.1% de spread
                    console.log(`📈 ${buyExchange} → ${sellExchange}`);
                    console.log(`   Comprar: $${buyPrice}, Vender: $${sellPrice}`);
                    console.log(`   Spread: ${spread.toFixed(3)}% - Ganancia potencial: $${(1000 * spread / 100).toFixed(2)} por $1000`);
                    opportunityFound = true;
                }
            }
        }
    }
    
    if (!opportunityFound) {
        console.log('No se encontraron oportunidades de arbitraje significativas.');
    }
}

// Ejecutar test
testCCXT().catch(console.error);