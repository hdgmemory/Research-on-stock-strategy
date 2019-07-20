from utils import *

my_universe = {}
def get_my_cxg_universe(trade_calendar,sectorid):
    '''
    :param trade_calendar:交易日历
    :param sectorid:股池代码，默认为A股，该代码在wind的wset函数中可查
    :return:最后返回my_universe字典
    '''
    print("start get_my_cxg_universe")
    global my_universe
    for date in trade_calendar:
        print(date, end=' ')
        my_c_u = []
        data = w.wset("sectorconstituent", "date={};sectorid={};field=wind_code".format(date, sectorid))
        secIDs = data.Data[0]
        ipo_dates = w.wsd(secIDs, "ipo_date", date, date, "")
        ipo_dates = [i.strftime('%Y-%m-%d') for i in ipo_dates.Data[0]]
        dictis = dict(zip(ipo_dates, secIDs))
        for i in dictis.keys():
            if datetime.timedelta(days=360) > datetime.datetime.strptime(date, '%Y-%m-%d') - datetime.datetime.strptime(
                    i, '%Y-%m-%d') > datetime.timedelta(days=30):
                my_c_u.append(dictis[i])
        my_universe[date] = replace_suffix(my_c_u)
    print("end get_my_cxg_universe")
    return my_universe

def get_industry(trade_calendar,my_universe):
    '''
    获取各日各行业的所有成分股
    :param trade_calendar:交易日历
    :param my_universe:上个函数的返回值
    :return: {'2018-05-31': {'6101000000000000': ['603363.SH'],……},……}
    '''
    print("start get_industry")
    Industry = {}
    for date in trade_calendar:
        print(date, end=' ')
        industrys = Stock_Industry(date)
        # 获取行业划分成份股
        Constituent_Stocks = {}
        univ = my_universe[date]
        for s in industrys:
            tmp = Industry_Constituent_Stocks(s, date)
            tmp = replace_suffix(tmp)
            tmp = list(set(tmp).intersection(set(univ)))
            Constituent_Stocks[s] = tmp
        Industry[date] = Constituent_Stocks
    return Industry
w.start()
print(w.isconnected())
# -----------------------------------------
start = '2015-01-01'    #回测起始时间
end = '2015-02-01'      # 回测结束时间
period = 'M'             #周期选择:'M'为月，'W'为周，'D'为天，'Q'为季，'S'为半年，'Y'为年                           #股池名称
dict_name_code = {'A': 'a001010100000000',  # A股
                  'B': 'a001010600000000',  # B股
                  'shA': 'a001010200000000',  # 沪市A股
                  'szA': 'a001010300000000',  # 深证A股
                  'zxqyb': '1000009396000000',  # 中小企业板
                  'cyb': 'a001010r00000000'}  # 创业板
sectorid = dict_name_code['A']
trade_calendar = const_trade_calendar(beginDate=start, endDate=end, period=period)
get_my_cxg_universe(trade_calendar,sectorid)
get_industry(trade_calendar,my_universe)
w.stop()