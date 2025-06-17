// Lista exchanges disponibles con CCXT
const ccxt = require('ccxt');

console.log('🔗 EXCHANGES SOPORTADOS POR CCXT');
console.log(`Total de exchanges: ${ccxt.exchanges.length}`);
console.log('');

const availableExchanges = [];

for (const exchangeId of ccxt.exchanges) {
    try {
        const exchange = new ccxt[exchangeId]();
        
        const countries = Array.isArray(exchange.countries) ? 
            exchange.countries.join(', ') : 
            exchange.countries || 'N/A';
            
        const website = Array.isArray(exchange.urls.www) ? 
            exchange.urls.www[0] : 
            exchange.urls.www || 'N/A';
        
        availableExchanges.push({
            id: exchangeId,
            name: exchange.name,
            countries: countries,
            website: website,
            hasSpot: exchange.has['spot'] || false,
            rateLimit: exchange.rateLimit || 'N/A'
        });
        
    } catch (error) {
        // Skip exchanges with initialization errors
    }
}

// Ordenar por nombre
availableExchanges.sort((a, b) => a.name.localeCompare(b.name));

// Mostrar exchanges principales para trading
console.log('📊 EXCHANGES PRINCIPALES PARA ARBITRAJE:');
const majorExchanges = availableExchanges.filter(ex => 
    ['binance', 'okx', 'gate', 'mexc', 'kucoin', 'bybit', 'bitget', 'huobi', 'kraken'].includes(ex.id)
);

majorExchanges.forEach(ex => {
    console.log(`${ex.name.padEnd(15)} | ${ex.id.padEnd(12)} | ${ex.countries}`);
});

console.log('');
console.log('🌍 EXCHANGES DISPONIBLES DESDE UBICACIONES RESTRINGIDAS:');
const workingExchanges = ['gate', 'mexc', 'okx', 'bitget', 'htx'];
workingExchanges.forEach(id => {
    const ex = availableExchanges.find(e => e.id === id);
    if (ex) {
        console.log(`✅ ${ex.name} (${ex.id}) - ${ex.countries}`);
    }
});

console.log('');
console.log(`📈 Total de exchanges analizados: ${availableExchanges.length}`);
console.log('🎯 Exchanges recomendados para tu bot: Gate.io, MEXC, OKX, Bitget');