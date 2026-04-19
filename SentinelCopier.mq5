//+------------------------------------------------------------------+
//|  SentinelCopier.mq5                                              |
//|  XAUUSD Sentinel — Plan 2 Copy Trading EA                        |
//|                                                                  |
//|  Polls the Sentinel API every N seconds for a pending signal.    |
//|  When a signal arrives, places a market order with the           |
//|  prescribed SL/TP and acknowledges the signal so it is not       |
//|  acted on again.                                                 |
//|                                                                  |
//|  Settings:                                                       |
//|    ApiUrl      — base URL of your Sentinel server                |
//|    ApiKey      — your personal API key from the admin panel      |
//|    RiskPercent — % of balance to risk per trade (default 1.0)   |
//|    PollSeconds — how often to check for a new signal             |
//|    MagicNumber — unique ID for orders placed by this EA          |
//+------------------------------------------------------------------+
#property copyright "XAUUSD Sentinel"
#property version   "1.00"
#property strict

#include <Trade\Trade.mqh>
#include <Trade\SymbolInfo.mqh>

//── Inputs ────────────────────────────────────────────────────────────────────
input string ApiUrl      = "http://YOUR_SERVER_IP:8000"; // Sentinel server URL
input string ApiKey      = "YOUR_API_KEY_HERE";          // API key from admin panel
input double RiskPercent = 1.0;                          // % of balance per trade
input int    PollSeconds = 30;                           // polling interval
input int    MagicNumber = 20240101;                     // EA magic number
input bool   UseAdvisoryLot = false;                     // use server lot or recalculate locally

//── Globals ───────────────────────────────────────────────────────────────────
CTrade  trade;
datetime lastPoll = 0;

//── Init ──────────────────────────────────────────────────────────────────────
int OnInit()
{
   trade.SetExpertMagicNumber(MagicNumber);
   trade.SetDeviationInPoints(30);
   trade.SetTypeFilling(ORDER_FILLING_RETURN);

   // Verify API key on startup
   string pingUrl = ApiUrl + "/api/ea/ping?api_key=" + ApiKey;
   string result  = HttpGet(pingUrl);

   if(StringFind(result, "\"status\":\"ok\"") < 0)
   {
      Alert("SentinelCopier: API key invalid or server unreachable. Check ApiUrl and ApiKey.");
      return INIT_FAILED;
   }

   Print("SentinelCopier: Connected to Sentinel server. Polling every ", PollSeconds, "s.");
   return INIT_SUCCEEDED;
}

//── Main tick ─────────────────────────────────────────────────────────────────
void OnTick()
{
   if(TimeCurrent() - lastPoll < PollSeconds) return;
   lastPoll = TimeCurrent();

   string signalJson = HttpGet(ApiUrl + "/api/ea/signal?api_key=" + ApiKey);
   if(signalJson == "" || signalJson == "null") return;

   // Parse fields from JSON
   int    signalId    = (int)ParseInt(signalJson,   "\"id\":");
   string signal      = ParseStr(signalJson,         "\"signal\":");
   string symbol      = ParseStr(signalJson,         "\"symbol\":");
   double entryPrice  = ParseDouble(signalJson,      "\"entry_price\":");
   double sl          = ParseDouble(signalJson,      "\"sl\":");
   double tp          = ParseDouble(signalJson,      "\"tp\":");
   double atr         = ParseDouble(signalJson,      "\"atr\":");
   double advisoryLot = ParseDouble(signalJson,      "\"lot_size\":");

   if(signalId <= 0 || (signal != "BUY" && signal != "SELL"))
   {
      Print("SentinelCopier: Unrecognised signal payload — ", signalJson);
      return;
   }

   // Calculate lot locally unless using advisory lot
   double lot = UseAdvisoryLot ? advisoryLot : CalculateLot(symbol, sl, entryPrice);
   if(lot <= 0) { Print("SentinelCopier: Lot calculation failed — skipping signal."); return; }

   // Place trade
   bool ok = false;
   if(signal == "BUY")
      ok = trade.Buy(lot, symbol, 0, sl, tp, "Sentinel_" + IntegerToString(signalId));
   else
      ok = trade.Sell(lot, symbol, 0, sl, tp, "Sentinel_" + IntegerToString(signalId));

   if(ok)
   {
      Print("SentinelCopier: ", signal, " ", lot, " ", symbol, " placed. Ticket=", trade.ResultOrder());
      AckSignal(signalId);
   }
   else
   {
      Print("SentinelCopier: Order failed. Retcode=", trade.ResultRetcode(),
            " — ", trade.ResultComment());
   }
}

//── Helpers ───────────────────────────────────────────────────────────────────

double CalculateLot(string sym, double sl, double entry)
{
   double balance      = AccountInfoDouble(ACCOUNT_BALANCE);
   double riskAmount   = balance * RiskPercent / 100.0;
   double slDistance   = MathAbs(entry - sl);
   if(slDistance <= 0) return 0;

   double tickValue    = SymbolInfoDouble(sym, SYMBOL_TRADE_TICK_VALUE);
   double tickSize     = SymbolInfoDouble(sym, SYMBOL_TRADE_TICK_SIZE);
   if(tickSize <= 0 || tickValue <= 0) return 0;

   double lotRaw       = riskAmount / (slDistance / tickSize * tickValue);
   double lotStep      = SymbolInfoDouble(sym, SYMBOL_VOLUME_STEP);
   double lotMin       = SymbolInfoDouble(sym, SYMBOL_VOLUME_MIN);
   double lotMax       = SymbolInfoDouble(sym, SYMBOL_VOLUME_MAX);

   double lot = MathFloor(lotRaw / lotStep) * lotStep;
   lot = MathMax(lotMin, MathMin(lotMax, lot));
   return NormalizeDouble(lot, 2);
}

void AckSignal(int signalId)
{
   string url = ApiUrl + "/api/ea/signal/" + IntegerToString(signalId)
                + "/ack?api_key=" + ApiKey;
   HttpPost(url, "");
   Print("SentinelCopier: Acknowledged signal ", signalId);
}

//── Minimal HTTP helpers (MQL5 built-in WebRequest) ──────────────────────────

string HttpGet(string url)
{
   char   post[];
   char   result[];
   string headers = "Content-Type: application/json\r\n";
   string resHeaders;
   int    timeout = 10000;

   ResetLastError();
   int code = WebRequest("GET", url, headers, timeout, post, result, resHeaders);
   if(code < 0) { Print("SentinelCopier GET error: ", GetLastError(), " url=", url); return ""; }
   return CharArrayToString(result);
}

string HttpPost(string url, string body)
{
   char   post[];
   char   result[];
   StringToCharArray(body, post, 0, StringLen(body));
   string headers = "Content-Type: application/json\r\n";
   string resHeaders;
   int    timeout = 10000;

   ResetLastError();
   int code = WebRequest("POST", url, headers, timeout, post, result, resHeaders);
   if(code < 0) { Print("SentinelCopier POST error: ", GetLastError()); return ""; }
   return CharArrayToString(result);
}

//── JSON parsers (lightweight — no external lib needed) ───────────────────────

string ParseStr(string json, string key)
{
   int pos = StringFind(json, key);
   if(pos < 0) return "";
   pos += StringLen(key);
   // skip whitespace and quote
   while(pos < StringLen(json) && (StringGetCharacter(json, pos) == ' ' ||
         StringGetCharacter(json, pos) == ':')) pos++;
   if(StringGetCharacter(json, pos) == '"') pos++;
   string val = "";
   while(pos < StringLen(json))
   {
      ushort c = StringGetCharacter(json, pos++);
      if(c == '"') break;
      val += ShortToString(c);
   }
   return val;
}

double ParseDouble(string json, string key)
{
   int pos = StringFind(json, key);
   if(pos < 0) return 0;
   pos += StringLen(key);
   while(pos < StringLen(json) && (StringGetCharacter(json, pos) == ' ' ||
         StringGetCharacter(json, pos) == ':')) pos++;
   string val = "";
   while(pos < StringLen(json))
   {
      ushort c = StringGetCharacter(json, pos++);
      if((c < '0' || c > '9') && c != '.' && c != '-') break;
      val += ShortToString(c);
   }
   return StringToDouble(val);
}

long ParseInt(string json, string key)
{
   return (long)ParseDouble(json, key);
}
//+------------------------------------------------------------------+
