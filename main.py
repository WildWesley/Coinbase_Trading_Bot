# We're running it back, but with Crypto this time:
# Crypto seems to be a much more profitable and volatile market than stocks, so I think a bot
# in crypto currency will allow me to really see the power of these trading strategies that I'll
# be using. The goal is to use coinbase, but we'll see how plans change as the project moves along
import cbpro
import requests
import datetime
import pandas as pd
import matplotlib.pyplot as plt
import time


class CoinbaseBot:
    @staticmethod
    def get_start_time(end):
        """
        This function takes in an end time date and converts it to a start date 2 hours and 30 minutes prior
        """
        # 2022-03-30T22:36:37.0807Z
        end_list = (
            end.replace("-", " ").replace("T", " ").replace(":", " ").replace(".", " ")
        )
        end_list = end_list.split()[:-1]
        end_stamp = datetime.datetime(
            year=int(end_list[0]),
            month=int(end_list[1]),
            day=int(end_list[2]),
            hour=int(end_list[3]),
            minute=int(end_list[4]),
            second=int(end_list[5]),
        ).timestamp()

        start_stamp = end_stamp - 108000
        start_date = datetime.datetime.fromtimestamp(start_stamp)
        return start_date.strftime("%Y-%m-%dT%H:%M:%S")

    @staticmethod
    def get_usd_products(authenticated, blacklist):
        """
        This function uses the authenticated account object to return a filtered list of only
        the products that can be purchased and sold using USD
        """

        products = [product["id"] for product in authenticated.get_products()]
        usd_products = []
        for id in products:
            if id not in blacklist:
                split_id = id.split("-")
                if split_id[1] == "USD":
                    usd_products.append(id)

        return usd_products

    @staticmethod
    def grab_account_info(file):
        """
        This function takes my account info from the Info.txt file and feeds it into the main() function
        """

        with open(file, "r") as storage:
            lines = storage.readlines()
            public = lines[0].split("= ")[1].replace("\n", "")
            password = lines[1].split("= ")[1].replace("\n", "")
            secret = lines[2].split("= ")[1].replace("\n", "")
        return public, password, secret

    @staticmethod
    def get_current_price(product_id):
        """
        This function gets the most recent buy and ask price for a product
        """

        url = f"https://api.exchange.coinbase.com/products/{product_id}/ticker"
        headers = {"Accept": "application/json"}
        response = requests.request("GET", url, headers=headers)
        return response.json()

    @staticmethod
    def get_historical_prices(product_id, granularity, end):
        """
        This function returns a list of highs, lows, opens, and closes for a product from a designated start time
        to an end time, given a certain candle time length(granularity)
        """

        start = CoinbaseBot.get_start_time(end)
        url = f"https://api.exchange.coinbase.com/products/{product_id}/candles?granularity={granularity}&start={start}&end={end}"
        headers = {"Accept": "application/json"}
        response = requests.request("GET", url, headers=headers)
        return response.json()

    @staticmethod
    def get_ema(close_prices, span):
        """
        This function uses a list of the close prices to output a pandas array of emas for use in calculation.
        """

        stock_values = pd.DataFrame({"Values": close_prices})
        ema = stock_values.ewm(com=span).mean()
        return ema["Values"].tolist()

    @staticmethod
    def get_cross(short1, short2, long1, long2):
        """
        This function takes the four most recent data points, and tells whether or not the lines crossed up or down
        or neither if nothing happens
        """
        before_state = short1 - long1
        after_state = short2 - long2

        if before_state <= 0:
            before_state = "low"
        elif before_state > 0:
            before_state = "high"

        if after_state <= 0:
            after_state = "low"
        elif after_state > 0:
            after_state = "high"

        change = before_state + "-" + after_state
        return change

    @staticmethod
    def get_recommendation(price_data):
        """
        This function uses the get_cross() function result, along with ema's calculated with the
        get_ema() function to determine whether to buy or sell a stock
        """

        long_ema = CoinbaseBot.get_ema(price_data, 100)
        short_ema = CoinbaseBot.get_ema(price_data, 12)
        change = CoinbaseBot.get_cross(
            short_ema[-2], short_ema[-1], long_ema[-2], long_ema[-1]
        )
        if change == "low-high":
            return "buy", short_ema, long_ema
        elif change == "high-low":
            return "sell", short_ema, long_ema
        else:
            return "none", short_ema, long_ema

    @staticmethod
    def get_balance(product, account_assets):
        for asset in account_assets:
            if asset["currency"] == product.split("-")[0]:
                return asset["balance"]

    @staticmethod
    def graph_data(product, price_data, short_ema, long_ema):
        """
        This function saves an image of the stock standings when the bot makes a trade
        """
        plt.plot(price_data, label="Stock Values")
        plt.plot(short_ema, label="Short EMA")
        plt.plot(long_ema, label="Long EMA")
        plt.xlabel("Hours")
        plt.ylabel("Price")
        plt.savefig(f"Trade_Photos/{product}_for_{price_data[-1]}.png")
        plt.clf()


def main():
    """
    The structure of the main loop will be as follows:
     - Clients authenticated
     - While loop starts:
         - Current price pulled
         - History data pulled
         - Current price added to end of history
         - EMA's calculated
         - Checks for EMA cross:
             - If crossed short over long:
                 - Buy $X
             - Elif crossed short under long:
                 - Sell all assets available
    """
    input("You crazy??? Y/N\n")
    # The blacklist is all the crypto currencies that I think the bot would be wayyy to bad at trading. Mainly the ones that are binary looking.
    blacklist = ["PAX-USD", "UST-USD", "PRO-USD", "REP-USD", "USDT-USD", "MUSD-USD"]

    public, secret, password = CoinbaseBot.grab_account_info("Info.txt")
    auth_client = cbpro.AuthenticatedClient(public, secret, password)
    products = CoinbaseBot.get_usd_products(auth_client, blacklist)
    i = 0
    with open("Trades_Logged/trades_logged.txt", "w") as log:
        while True:
            account_assets = auth_client.get_accounts()
            for product in products:
                i += 1
                print(i)
                try:
                    # I'm pulling all the data necessary for calculations
                    current_price = CoinbaseBot.get_current_price(product)
                    recent_time = current_price["time"]
                    recent_price = float(current_price["ask"])
                    candles = CoinbaseBot.get_historical_prices(
                        product, "900", recent_time
                    )

                    # This is gonna get me my y axis for graphing
                    price_data = []
                    for candle in candles:
                        price_data.insert(0, float(candle[4]))
                    price_data.append(recent_price)

                    # Now we make our calculation and prediction
                    (
                        recommendation,
                        short_ema,
                        long_ema,
                    ) = CoinbaseBot.get_recommendation(price_data)
                    if recommendation == "buy":
                        # auth_client.place_market_order(
                        #     product_id=product, side="buy", funds=5.00
                        # )
                        log.write(f"Bought {product} for {recent_price}\n")
                        CoinbaseBot.graph_data(product, price_data, short_ema, long_ema)
                    elif recommendation == "sell":
                        # auth_client.place_market_order(
                        #     product_id=product,
                        #     side="sell",
                        #     size=CoinbaseBot.get_balance(product, account_assets),
                        # )
                        log.write(f"Sold {product} for {recent_price}\n")
                        CoinbaseBot.graph_data(product, price_data, short_ema, long_ema)
                except Exception as e:
                    print(e)
            time.sleep(180)


if __name__ == "__main__":
    main()
