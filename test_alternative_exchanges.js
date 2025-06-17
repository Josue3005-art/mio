// Test exchanges that work from restricted locations
const ccxt = require('ccxt');

async function testAlternativeExchanges() {
    console.log('🌍 Probando exchanges alternativos disponibles...');
    
    // Exchanges que típicamente funcionan desde ubicaciones restringidas
    const exchangeConfigs = [
        { name: 'gate', displayName: 'Gate.io' },
        { name: 'mexc', displayName: 'MEXC' },
        { name: 'bybit', displayName: 'Bybit' },
        { name: 'okx', displayName: 'OKX' },
        { name: 'bitget', displayName: 'Bitget' },
        { name: 'htx', displayName: 'HTX (Huobi)' }
    ];
    
    const workingExchanges = [];
    
    for (const config of exchangeConfigs) {
        try {
            console.log(`\n--- ${config.displayName} ---`);
            
            const exchange = new ccxt[config.name]({
                sandbox: false,
                enableRateLimit: true,
            });
            
            // Test básico: obtener ticker
            const ticker = await exchange.fetchTicker('BTC/USDT');
            console.log(`✅ Conectado - BTC/USDT: $${ticker.last}`);
            
            // Test libro de órdenes
            const orderBook = await exchange.fetchOrderBook('BTC/USDT', 5);
            const spread = ((orderBook.asks[0][0] - orderBook.bids[0][0]) / orderBook.bids[0][0] * 100).toFixed(4);
            console.log(`✅ Spread: ${spread}% (Bid: $${orderBook.bids[0][0]}, Ask: $${orderBook.asks[0][0]})`);
            
            workingExchanges.push({
                name: config.name,
                displayName: config.displayName,
                price: ticker.last,
                bid: orderBook.bids[0][0],
                ask: orderBook.asks[0][0],
                spread: parseFloat(spread)
            });
            
        } catch (error) {
            console.log(`❌ ${config.displayName}: ${error.message.split('\n')[0]}`);
        }
    }
    
    // Análisis de arbitraje entre exchanges disponibles
    if (workingExchanges.length >= 2) {
        console.log('\n🔍 OPORTUNIDADES DE ARBITRAJE DETECTADAS:');
        
        for (let i = 0; i < workingExchanges.length; i++) {
            for (let j = 0; j < workingExchanges.length; j++) {
                if (i !== j) {
                    const buyEx = workingExchanges[i];
                    const sellEx = workingExchanges[j];
                    
                    const buyPrice = buyEx.ask;
                    const sellPrice = sellEx.bid;
                    const spreadPct = ((sellPrice - buyPrice) / buyPrice) * 100;
                    
                    if (spreadPct > 0.1) {
                        console.log(`📈 ${buyEx.displayName} → ${sellEx.displayName}`);
                        console.log(`   Comprar: $${buyPrice}, Vender: $${sellPrice}`);
                        console.log(`   Spread: ${spreadPct.toFixed(3)}% - Ganancia potencial: $${(30 * spreadPct / 100).toFixed(2)} con $30`);
                    }
                }
            }
        }
        
        if (workingExchanges.length === 0) {
            console.log('No se encontraron oportunidades significativas en este momento.');
        }
    }
    
    // Resumen
    console.log(`\n📊 RESUMEN:`);
    console.log(`Exchanges funcionales: ${workingExchanges.length}`);
    if (workingExchanges.length > 0) {
        console.log('Exchanges disponibles para arbitraje:');
        workingExchanges.forEach(ex => {
            console.log(`  - ${ex.displayName}: $${ex.price} (spread: ${ex.spread}%)`);
        });
    }
}

testAlternativeExchanges().catch(console.error);