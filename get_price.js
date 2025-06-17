const ccxt = require('ccxt');

async function getPrice(exchangeId, symbol) {
    try {
        const exchange = new ccxt[exchangeId]({
            sandbox: false,
            enableRateLimit: true,
        });
        
        const ticker = await exchange.fetchTicker(symbol);
        const orderBook = await exchange.fetchOrderBook(symbol, 5);
        
        console.log(JSON.stringify({
            exchange: exchangeId,
            symbol: symbol,
            bid: ticker.bid,
            ask: ticker.ask,
            last: ticker.last,
            volume: ticker.baseVolume,
            spread: ((ticker.ask - ticker.bid) / ticker.bid * 100).toFixed(4)
        }));
    } catch (error) {
        console.error(JSON.stringify({error: error.message}));
    }
}

const args = process.argv.slice(2);
if (args.length === 2) {
    getPrice(args[0], args[1]);
} else {
    console.error(JSON.stringify({error: "Usage: node get_price.js <exchangeId> <symbol>"}));
}


