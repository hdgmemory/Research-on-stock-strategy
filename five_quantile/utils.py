from WindPy import *
import numpy as np
import pandas as pd
import statsmodels.api as sm
from functools import wraps,reduce
import datetime
import time
import json
import os
import warnings
warnings.filterwarnings("ignore")
# import matplotlib.pylab as plt
# import seaborn as sns

'''
本地化存在的问题：1、分位数去极值tmp[tmp<l]那里有warning
2、accumAdjFactor出的值和优矿上的值不同
'''


def wrapper_func_cache(func):
    '''
    装饰器，缓存已经运行过的日期存放在__cache_result变量中
    :param func:
    :return:
    '''
    @wraps(func)  # 把原始函数__name__等属性复制到wrapped
    def wrapped(*args, **kwargs):
        if not hasattr(func, '__cache_result'):  # hasattr（object,name）判断一个对象是否包含对应的属性
            func.__cache_result = {}  # 如果不存在对应属性，初始化为空dict
        hash_key = [str(i) for i in args] + [str(j) for j in kwargs.items()]  # hashkey为字符串list
        cache_key = hash(tuple(hash_key))  # cachekey为hashkey转化的hash值
        if cache_key not in func.__cache_result:  # 如果cachekey不存在于__cache_result结果中
            func.__cache_result[cache_key] = func(*args, **kwargs)  # 将对象存储在对应cachekey位置
        return func.__cache_result[cache_key]  # 返回函数func(*args,**kwargs)
    return wrapped


@wrapper_func_cache  # 相当于执行了Monthly_const_trade_calendar = wrapper_func_cache（Monthly_const_trade_calendar）
def const_trade_calendar(beginDate, endDate, period='M'):
    '''
    交易日历，可以选择cache，只调用 api 一次。（cache缓存库）
    :param beginDate:
    :param endDate:
    :param period:'D'
    :return:
    '''
    #筛选交易日历形式
    if period =='M':
        delta = datetime.timedelta(days=31)
    elif period=='W':
        delta = datetime.timedelta(days=7)
    elif period=='Q':
        delta = datetime.timedelta(days=92)
    elif period=='Y':
        delta = datetime.timedelta(days=366)
    else:
        delta = datetime.timedelta(days=1)
    new_end_date = (datetime.datetime.strptime(endDate, '%Y-%m-%d') + delta).strftime('%Y-%m-%d')

    #利用交集去掉最后一个非周期末交易日的日期
    # 沪市日期
    dates1 = w.tdays("{}".format(beginDate), "{}".format(endDate), "Period={}".format(period))
    new_dates1 = w.tdays("{}".format(beginDate), "{}".format(new_end_date), "Period={}".format(period))
    # 深市日期
    dates2 = w.tdays("{}".format(beginDate), "{}".format(endDate), "Period={};TradingCalendar=SZSE".format(period))
    new_dates2 = w.tdays("{}".format(beginDate), "{}".format(new_end_date), "Period={};TradingCalendar=SZSE".format(period))
    #sh_calendar：沪市交易日历; sz_calendar：深市交易日历
    sh_calendar = [v.strftime('%Y-%m-%d') for v in dates1.Data[0] if v in new_dates1.Data[0]]#取交集，得到各个月末交易日
    sz_calendar = [v.strftime('%Y-%m-%d') for v in dates2.Data[0] if v in new_dates2.Data[0]]
    #两个交易所的交易日历取并集
    trade_calendar = sorted(list(set(sh_calendar).union(set(sz_calendar))))
    return trade_calendar


def set_universe( dict_name_code,block_name, dates,):
    '''
    获得沪深股市在dates日期内的A股（次新股）股池
    :param dates: 具体某个日期
    :return codelist: 沪深股市A股（次新股）代码list
    '''
    if block_name in list(dict_name_code.keys()):
        data = w.wset("sectorconstituent", "date={};sectorid={};field=wind_code".format(dates, dict_name_code[block_name]))
        universe = data.Data[0]
    elif block_name == 'cxg':
        data = w.wset("sectorconstituent", "date={};sectorid=a001010100000000;field=wind_code".format(dates))
        secIDs = data.Data[0]
        universe = []
        for stk in secIDs:
            ipo_date = w.wsd(stk, "ipo_date", dates, dates, "")
            ipo_date = ipo_date.Data[0][0]
            if datetime.timedelta(days=360) > (datetime.datetime.strptime(dates, '%Y-%m-%d') - ipo_date) > \
                    datetime.timedelta(days=30):
                universe.append(stk)
    else:
        pass
    # print(universe)
    return universe


def st_remove(source_universe, st_date=None):
    '''
    给定股票列表,去除其中在某日被标为ST的股票
    Args:
        source_universe (list of str): 需要进行筛选的股票列表，源列表包含全部股票
        st_date (datetime): 进行筛选的日期,默认为调用当天
    Returns:
        list: 去掉ST股票之后的股票列表
    '''
    data = w.wset("sectorconstituent", "date={};sectorid=1000006526000000;field=wind_code".format(st_date))
    st_list = data.Data[0]
    return [s for s in source_universe if s not in st_list]  # 返回source_universe中所有不在df_ST表中的


def winsorize_median(tmp):
    '''
    分位数去极值。参考“选股因子数据的异常值处理和正态转换中的‘1.2.4 boxplot法’”
    :param tmp: pd.Series
    :return: pd.Series
    '''
    if isinstance(tmp, pd.Series):  # isinstance（object,classinfo）判断一个对象是否是一个已知的类型
        mc = sm.stats.stattools.medcouple(tmp)  # medcouple（）用于识别非对称分布的异常值,向右倾斜的分布是正的，对于向左倾斜的分布是负的，对称分布是零
        data = sorted(tmp)  # sorted() 函数对所有可迭代的对象进行 排序操作，返回一个新的 list
        q1 = np.percentile(data, 25)  # 计算一个多维数组的任意百分比分位数的数值，25%分位数
        q3 = np.percentile(data, 75)
        iqr = q3 - q1
        if mc >= 0:  # mc表示样本偏度，当样本数据分布右偏时，提升正常数据区间上限的数值；样本数据左偏时，则会降低正常数据区间下限的数值。
            l = q1 - 1.5 * np.exp(-3.5 * mc) * iqr
            u = q3 + 1.5 * np.exp(4 * mc) * iqr
        else:
            l = q1 - 1.5 * np.exp(-4 * mc) * iqr
            u = q3 + 1.5 * np.exp(3.5 * mc) * iqr
        tmp[tmp < l] = l
        tmp[tmp > u] = u
    return tmp


def standardize_zscore(tmp):
    '''
    函数封装问题（标准化：z-score使得平均值为0，标准差为1）
    标准化：将去极值处理后的因子暴露度序列减去其现在的均值、除以其标准差，得到一个新的近似服从N(0,1)分布的序列，
    这样做可以让不同因子的暴露度之间具有可比性
    :param tmp:
    :return:
    '''
    if isinstance(tmp, pd.Series):
        mu = tmp.mean()  # 均值
        sigma = tmp.std()  # 标准差
        tmp = (tmp - mu) / sigma
    return tmp


def Stock_Industry(point):
    '''
    根据日期判断行业分类采用新版还是旧版
    :param point: 日期字符串
    :return:行业列表
    '''
    SW_Old = ['6101000000000000', '6102000000000000', '6103000000000000', '6104000000000000', \
              '6105000000000000', '6108000000000000', '6111000000000000', '6112000000000000', \
              '6113000000000000', '6114000000000000', '6115000000000000', '6116000000000000', \
              '6117000000000000', '6118000000000000', '6120000000000000', '6121000000000000', \
              '6123000000000000']
    SW_New = ['6101000000000000', '6102000000000000', '6103000000000000', '6104000000000000', \
              '6105000000000000', '6108000000000000', '6111000000000000', '6112000000000000', \
              '6113000000000000', '6114000000000000', '6115000000000000', '6116000000000000', \
              '6117000000000000', '6118000000000000', '6120000000000000', '6121000000000000', \
              '6123000000000000', '6106010000000000', '6106020000000000', '6107010000000000', \
              '1000012579000000', '1000012601000000', '6122010000000000', '1000012611000000', \
              '1000012612000000', '1000012613000000', '1000012588000000', '6107000000000000']
    if isinstance(point, str):
        point = pd.to_datetime(point)
    else:
        print('time point type wrong')
    timepoint = pd.to_datetime('2014-01-01')
    if point <= timepoint:
        return SW_Old
    elif point > timepoint:
        return SW_New
    else:
        print('wrong')


def Industry_Constituent_Stocks(industry, timepoint):
    '''
    获取申万一级行业分类成份股
    :param industry: 行业编码
    :param timepoint: 日期字符串
    :return: 行业industry的成份股列表
    '''
    # tmp = DataAPI.IdxConsGet(ticker=industry, intoDate=timepoint, isNew=u"", field=['consID'],
    #                          pandas="1")  # industry为成分股的编码，timepoint为获取日的时间
    data = w.wset("sectorconstituent", date=timepoint, sectorid=industry, field="wind_code")
    return (sorted(list(data.Data[0])))


# 新增Part


def get_R_index(stock_code,beginDate,endDate,period):
    '''
    获取参考指数收益率，例如HS300
    :param stock_code:参照股的代码
    :param beginDate:起始日期
    :param endDate:结束日期
    :param period:周期
    :return:
    '''
    # R_index = DataAPI.MktIdxmGet(beginDate=u"20150101", endDate=u"20170510", indexID=u"000300.ZICN", ticker=u"",
    #                              field=['endDate', 'closePrice'], pandas="1")
    d = w.wsd(stock_code, "close", beginDate, endDate, "Period={}".format(period))
    # print(d)
    endDate_list = [i.strftime('%Y-%m-%d') for i in d.Times]
    temp = {
        'endDate': endDate_list,
        'closePrice': d.Data[0],
    }
    # print(temp)
    R_index = pd.DataFrame(temp)
    R_index.sort_values('endDate', inplace=True)
    # print(R_index.closePrice)
    R_index['R_index'] = np.log(R_index.closePrice.shift(-1) / R_index.closePrice)#上一个日期的收盘价/本日期收盘价=收益率
    R_index.set_index('endDate', inplace=True)
    return R_index


def get_Pricefront(univ,date):
    '''
    获取前复权价格
    :param univ:股票代码列表
    :param date:日期
    :return:DataFrame（股票代码，收盘价，累计复权因子，净市值，前复权价格）
    '''
    # Price_front = DataAPI.MktEqudGet(tradeDate=date, secID=univ, beginDate=u"", endDate=u"", isOpen="1",
    #                                  field=['secID', 'closePrice', 'accumAdjFactor', 'negMarketValue'], pandas="1")
    d = w.wss(univ, "windcode,close,adjfactor,mkt_cap_float",
              "tradeDate={};priceAdj=U;cycle=D;unit=1;currencyType=".format(date))
    # print(d)
    temp = {
        'secID': d.Data[0],
        'closePrice': d.Data[1],
        'accumAdjFactor': d.Data[2],
        'negMarketValue': d.Data[3]
    }
    Price_front = pd.DataFrame(temp)
    Price_front.eval('front=closePrice/accumAdjFactor', inplace=True)
    return Price_front


def get_Pricebehind(univ,date_next):
    '''
    获取后复权价格
    :param univ:股票代码列表
    :param date_next:一周期后的交易日
    :return:DataFrame（股票代码，收盘价，累计复权因子，后复权价格）
    '''
    # Price_behind = DataAPI.MktEqudGet(tradeDate=date_next, secID=univ, beginDate=u"", endDate=u"", isOpen="",
    #                                   field=['secID', 'closePrice', 'accumAdjFactor'], pandas="1")
    d = w.wss(univ, "windcode,close,adjfactor",
              "tradeDate={};priceAdj=U;cycle=D;unit=1;currencyType=".format(date_next))
    temp = {
        'secID': d.Data[0],
        'closePrice': d.Data[1],
        'accumAdjFactor': d.Data[2],
    }
    Price_behind = pd.DataFrame(temp)
    Price_behind.eval('behind=closePrice/accumAdjFactor', inplace=True)
    return Price_behind


def get_factor_loadings(univ,fac,date,file_prefix = 'F:/factors/'):
    '''
    C:/Users/MSI-PC/Desktop/
    注意：此处if中仅选择了pb，pe，ps三个因子作为直接可取的因子，但实际上并不知这三个，未来可按要求继续添加
    获取横截面（某日）的目标股池的因子载荷值。与get_factor区别在于增加了对数据的标准化
    :param univ: 股池
    :param fac: 因子名称
    :param date: 日期
    :return: DataFrame（股票代码，因子值）
    '''

    if fac is not None:
        # if fac == 'PE':
        #     rt = 10
        # elif fac == 'PB':
        #     rt = 3
        # elif fac == 'PS':
        #     rt = 2
        # else:
        #     pass
        # factor_loadings = DataAPI.MktStockFactorsOneDayGet(tradeDate=date, secID=univ, field=['secID'] + [fac], pandas="1")
        #d = w.wss(codes=univ, fields=["windcode", list(fac.keys())[0]], tradeDate=date, ruleType=list(fac.values())[0])
        for k,v in fac.items():
            d = w.wss(codes=univ, fields=["windcode", k], tradeDate=date, ruleType=v)
            temp = {
                'secID': d.Data[0],
                str(k): d.Data[1],
            }
            factor_loadings = pd.DataFrame(temp)
            #if list(fac.keys())[0] == 'PE' or list(fac.keys())[0] == 'PB' or list(fac.keys())[0] == 'PS':
            if fac is not None:
                factor_loadings[k] = 1.0 / factor_loadings[k]
            factor_loadings[k] = standardize_zscore(winsorize_median(factor_loadings[k]))
            factor_loadings.set_index('secID', inplace=True)
            # print('开始----------------------')
            # print(factor_loadings)
            return factor_loadings
    else:# readcsv
        factor_loadings = pd.read_csv(file_prefix+'fac_value.csv',usecols=['secID','date',fac])
        factor_loadings.dropna(inplace=True)
        factor_loadings.set_index('date', inplace=True)
        factor_loadings = factor_loadings.loc[date]
        factor_loadings[fac] = standardize_zscore(winsorize_median(factor_loadings[fac]))
        factor_loadings.set_index('secID', inplace=True)
        print('开始----------------------')
        print(factor_loadings)
        return factor_loadings


def get_Linear_Regression(date, univ, factor_loadings):
    '''
    获取行业暴露度,哑变量矩阵
    :param date:日期
    :param univ:股池
    :param factor_loadings:因子载荷，上一个函数的返回结果
    :return:经筛选后的DataFrame（股票代码，fac）
    '''
    SW_Industry_List = Stock_Industry(date)     #获取申万一级行业分类
    print(SW_Industry_List)
    Linear_Regression = pd.DataFrame()          #初始化线性回归DataFrame
    for i in SW_Industry_List:
        i_Constituent_Stocks = Industry_Constituent_Stocks(i, date)                     # 获取行业i的成分股
        i_Constituent_Stocks = list(set(i_Constituent_Stocks).intersection(set(univ)))  # 取得行业分类成分股和筛选过后的A股股票代码的交集
        try:
            tmp = factor_loadings.loc[i_Constituent_Stocks]  # 行业i筛选出来的股票，两列，股票代码+PB
            tmp.dropna(inplace=True)  # 直接删除tmp中有空值的行
            tmp[i] = 1.0  # 新增列，类名为行业分类代码，值为1.0，tmp变为股票代码+PB+i，i为行业分类编码
        except:
            print('no new column in '+i)
        Linear_Regression = Linear_Regression.append(tmp, sort=False)#
    Linear_Regression.fillna(0.0, inplace=True)#用0填充空值
    return Linear_Regression

'''
优矿部分应用的函数
'''
def read_txt(filename, readmode ='r'):
    '''
    读取txt文件
    :param filename:txt文件名
    :param readmode:读取模式
    :return:dict
    '''
    with open(filename, readmode) as f:
        js = f.read()
        inputs = json.loads(js)
        # inputs = pickle.load(f)
    return inputs
    # with open(filename, readmode) as f:
    #     inputs = pickle.load(f)
    # return inputs


def replace_suffix(l):
    '''
    更改股票代码的后缀，以使其与优矿的接口契合
    :param l:替换前的列表('SZ','SH')
    :return:替换后的列表('XSHE','XSHG')
    '''
    for i in range(len(l)):
        if 'SZ' in l[i]:
            l[i] = l[i].replace('SZ', 'XSHE')
        else:
            l[i] = l[i].replace('SH', 'XSHG')
    return l


def regain_suffix(l):
    '''
    更改股票代码的后缀，以使其与万得的接口契合
    :param l:替换前的列表('XSHE','XSHG')
    :return:替换后的列表('SZ','SH')
    '''
    for i in range(len(l)):
        if 'XSHE' in l[i]:
            l[i] = l[i].replace('XSHE', 'SZ')
        else:
            l[i] = l[i].replace('XSHG', 'SH')
    return l


def get_factor(univ,k,v, date, file_prefix):
    '''
    用于getfivequantilecsv，与上方的get_factor_loadings区别仅在缺少标准化standardize_zscore(winsorize_median(factor_loadings[fac]))
    是服务于优矿的函数
    :param univ: 股池
    :param fac: 因子名
    :param date: 日期
    :param file_prefix: from_where，文件路径
    :return:
    '''
    if k is not None:
        # if fac == 'PE':
        #     rt = 10
        # elif fac == 'PB':
        #     rt = 3
        # elif fac == 'PS':
        #     rt = 2
        # else:
        #     pass
        d = w.wss(codes=univ, fields=["windcode", k], tradeDate=date, ruleType=v)
        temp = {
            'secID': replace_suffix(d.Data[0]),
             str(k): d.Data[1],
        }
        factor = pd.DataFrame(temp)
        #if fac == 'PE' or fac == 'PB' or fac == 'PS':
        if k is not None:
            factor[k] = 1.0 / factor[k]
        factor.dropna(inplace=True)
        factor.set_index('secID', inplace=True)
        return factor
    else:# readcsv
        factor = pd.read_csv(file_prefix+'fac_value.csv',usecols=['secID','date',k])
        factor.dropna(inplace=True)
        factor.set_index('date', inplace=True)
        factor = factor.loc[date]
        factor['secID'] = replace_suffix(k['secID'].tolist())
        factor.set_index('secID', inplace=True)
        return factor