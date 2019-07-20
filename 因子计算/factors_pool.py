from WindPy import *
import pandas as pd
from functools import reduce
import sys
import math
import statsmodels.api as sm
import numpy as np

w.start(waitTime=60)
w.isconnected()


def get_fac_list():
    # return [EPcut, FCFP, rating_change, rating_targetprice, std_turn_1w, std_turn_2w, std_turn_4w, std_turn_12w,
    #         bias_std_turn_1w, bias_std_turn_2w, bias_std_turn_4w, weighted_strength_1w, weighted_strength_2w,
    #         weighted_strength_4w, weighted_strength_12w, exp_wgt_return_1w, exp_wgt_return_2w, exp_wgt_return_4w,
    #         exp_wgt_return_12w, HAlpha, beta_consistence, id1_std_3m, id2_std_3m, id2_std_up_3m, id2_std_down_3m,
    #          high_r_std_3m, low_r_std_3m, hml_r_std_3m, hpl_r_std_3m, financial_leverage,debtequityratio, marketvalue_leverage]
    return
    # 估值
def EPcut(univ, begin, end, period):
    # 获取数据
    fac = sys._getframe().f_code.co_name  # 因子名称
    wind_fac = "val_pe_deducted_ttm"  # WIND因子名称
    data = w.wsd(univ, wind_fac, begin, end, "Period={}".format(period))  # 按周获取数据

    # 整理成DataFrame，一共3列，分别是股票代码、日期和因子值
    col_date = [v.strftime("%Y-%m-%d") for v in data.Times] * len(data.Codes)
    col_code = [[i] * len(data.Times) for i in data.Codes]
    col_code = reduce(lambda x, y: x + y, col_code)
    col_fac = reduce(lambda x, y: x + y, data.Data)
    df = pd.DataFrame({"secID": col_code, "date": col_date, wind_fac: col_fac})
    # 计算因子值：取倒数，前推12个月扣除非经常性损益后的净利润/总市值
    df[fac] = 1 / df[wind_fac]
    #修改（增加）
    df["date"] = sorted(df["date"])
    df["secID"] = sorted(df["secID"])
    # 保留三列
    df = df[["date","secID",  fac]]
    return df


def FCFP(univ, begin, end, period):
    # 获取数据
    fac = sys._getframe().f_code.co_name  # 因子名称
    wind_fac = "val_mvtofcff"  # WIND因子名称
    data = w.wsd(univ, wind_fac, begin, end, "Period={}".format(period))  # 按周获取数据

    # 整理成DataFrame，一共3列，分别是股票代码、日期和因子值
    col_date = [v.strftime("%Y-%m-%d") for v in data.Times] * len(data.Codes)
    col_code = [[i] * len(data.Times) for i in data.Codes]
    col_code = reduce(lambda x, y: x + y, col_code)
    col_fac = reduce(lambda x, y: x + y, data.Data)
    df = pd.DataFrame({"secID": col_code, "date": col_date, wind_fac: col_fac})

    # 计算因子值:取倒数,自由现金流（最新年报）/总市值
    df[fac] = 1 / df[wind_fac]

    # 保留三列
    df = df[["date", "secID", fac]]
    return df


def rating_change(univ, begin, end, period):
    # 获取数据
    fac = sys._getframe().f_code.co_name  # 因子名称
    wind_fac = ["rating_instnum", "rating_upgrade", "rating_downgrade"]  # WIND因子名称
    data = {}
    for i in wind_fac:
        data[i] = w.wsd(univ, i, begin, end, "Period={}".format(period))  # 按周获取数据

    # 整理成DataFrame，按列分别是股票代码、日期和待计算因子值
    col_date = [v.strftime("%Y-%m-%d") for v in data[wind_fac[0]].Times] * len(data[wind_fac[0]].Codes)
    col_code = [[i] * len(data[wind_fac[0]].Times) for i in data[wind_fac[0]].Codes]
    col_code = reduce(lambda x, y: x + y, col_code)
    df = pd.DataFrame({"secID": col_code, "date": col_date})
    for i in wind_fac:  # 按列添加待计算因子值
        col_fac = reduce(lambda x, y: x + y, data[i].Data)
        df[i] = pd.Series(col_fac)

    # 计算因子值：（(上调数-下调数)/总评级数）
    df[fac] = (df["rating_upgrade"] - df["rating_downgrade"]) / df["rating_instnum"]

    # 保留三列
    df = df[["date", "secID", fac]]
    return df


def rating_targetprice(univ, begin, end, period):
    # 获取数据
    fac = sys._getframe().f_code.co_name  # 因子名称
    wind_fac = ["wrating_targetprice", "close"]  # WIND因子名称
    data = {}
    for i in wind_fac:
        data[i] = w.wsd(univ, i, begin, end, "Period={}".format(period))  # 按周获取数据

    # 整理成DataFrame，按列分别是股票代码、日期和待计算因子值
    col_date = [v.strftime("%Y-%m-%d") for v in data[wind_fac[0]].Times] * len(data[wind_fac[0]].Codes)
    col_code = [[i] * len(data[wind_fac[0]].Times) for i in data[wind_fac[0]].Codes]
    col_code = reduce(lambda x, y: x + y, col_code)
    df = pd.DataFrame({"secID": col_code, "date": col_date})
    for i in wind_fac:  # 按列添加待计算因子值
        col_fac = reduce(lambda x, y: x + y, data[i].Data)
        df[i] = pd.Series(col_fac)

    # 计算因子值：（一致目标价/现价-1）
    df[fac] = df["wrating_targetprice"] / df["close"] - 1

    # 保留三列
    df = df[["date", "secID", fac]]
    return df


# 换手率
def std_turn_1w(univ, begin, end, period):
    # 获取数据
    fac = sys._getframe().f_code.co_name  # 因子名称
    wind_fac = ["turn"]  # WIND因子名称
    win = 5  # 窗口为5天
    # 获取开始时间的前5个交易日
    begin_p = w.tdaysoffset(-win, begin)
    begin_p = begin_p.Times[0]
    data = w.wsd(univ, wind_fac, str(begin_p), end, "")  # 按日获取
    # 整理成二维表格，行为日期，列为股票代码，用于计算
    raw_df = pd.DataFrame(columns=data.Codes)
    for i in range(len(data.Codes)):
        raw_df[data.Codes[i] + 'old'] = pd.Series(data.Data[i])

    # 计算5日换手率标准差
    for code in data.Codes:
        raw_df[code] = raw_df[code + 'old'].rolling(win).std()  # 滚动
    raw_df = raw_df[data.Codes]
    raw_df['date'] = pd.Series(data.Times)  # 添加日期

    # 按周获取参照日期
    date_ref = w.tdays(begin, end, "Period={}".format(period))
    raw_df = raw_df[raw_df['date'].isin(date_ref.Times)]
    raw_df = raw_df.set_index("date")
    # 变形为三列，分别为股票代码、日期和因子值
    df = raw_df.stack().reset_index()
    # 修改（增加1行）
    df.rename(columns={ "level_1": "secID", 0: fac}, inplace=True)
    #df.rename(columns={"level_0": "date", "level_1": "secID", 0: fac}, inplace=True)
    #修改（增加1行）
    df["secID"] = sorted(df["secID"])
    # 修改（增加一行）
    df["date"] = sorted(df["date"])
    df["date"] = df["date"].apply(lambda x:x.strftime("%Y-%m-%d"))  # 转为换日期字符串格式
    return df

def std_turn_2w(univ, begin, end, period):
    # 获取数据
    fac = sys._getframe().f_code.co_name  # 因子名称
    wind_fac = ["turn"]  # WIND因子名称
    win = 10  # 窗口为10天
    # 获取开始时间的前10个交易日
    begin_p = w.tdaysoffset(-win, begin)
    begin_p = begin_p.Times[0]
    data = w.wsd(univ, wind_fac, str(begin_p), end, "")  # 按日获取

    # 整理成二维表格，行为日期，列为股票代码，用于计算
    raw_df = pd.DataFrame(columns=data.Codes)
    for i in range(len(data.Codes)):
        raw_df[data.Codes[i] + 'old'] = pd.Series(data.Data[i])

    # 计算10日换手率标准差
    for code in data.Codes:
        raw_df[code] = raw_df[code + 'old'].rolling(win).std()  # 滚动
    raw_df = raw_df[data.Codes]
    raw_df['date'] = pd.Series(data.Times)  # 添加日期

    # 按周获取参照日期
    date_ref = w.tdays(begin, end, "Period={}".format(period))
    raw_df = raw_df[raw_df['date'].isin(date_ref.Times)]

    # 变形为三列，分别为股票代码、日期和因子值
    raw_df = raw_df.set_index("date")
    df = raw_df.stack().reset_index()
    df.rename(columns={ "level_1": "secID", 0: fac}, inplace=True)
    df["date"] = df["date"].apply(lambda x: x.strftime("%Y-%m-%d"))  # 转换日期为字符串格式
    return df


def std_turn_4w(univ, begin, end, period):
    # 获取数据
    fac = sys._getframe().f_code.co_name  # 因子名称
    wind_fac = ["turn"]  # WIND因子名称
    win = 20  # 窗口为20天
    # 获取开始时间的前20个交易日
    begin_p = w.tdaysoffset(-win, begin)
    begin_p = begin_p.Times[0]
    data = w.wsd(univ, wind_fac, str(begin_p), end, "")  # 按日获取

    # 整理成二维表格，行为日期，列为股票代码，用于计算
    raw_df = pd.DataFrame(columns=data.Codes)
    for i in range(len(data.Codes)):
        raw_df[data.Codes[i] + 'old'] = pd.Series(data.Data[i])

    # 计算20日换手率标准差
    for code in data.Codes:
        raw_df[code] = raw_df[code + 'old'].rolling(win).std()  # 滚动
    raw_df = raw_df[data.Codes]
    raw_df['date'] = pd.Series(data.Times)  # 添加日期

    # 按周获取参照日期
    date_ref = w.tdays(begin, end, "Period={}".format(period))
    raw_df = raw_df[raw_df['date'].isin(date_ref.Times)]

    # 变形为三列，分别为股票代码、日期和因子值
    raw_df = raw_df.set_index("date")
    df = raw_df.stack().reset_index()
    df.rename(columns={"level_1": "secID", 0: fac}, inplace=True)
    df["date"] = df["date"].apply(lambda x: x.strftime("%Y-%m-%d"))  # 转换日期为字符串格式
    return df


def std_turn_12w(univ, begin, end, period):
    # 获取数据
    fac = sys._getframe().f_code.co_name  # 因子名称
    wind_fac = ["turn"]  # WIND因子名称
    win = 60  # 窗口为60天
    # 获取开始时间的前60个交易日
    begin_p = w.tdaysoffset(-win, begin)
    begin_p = begin_p.Times[0]
    data = w.wsd(univ, wind_fac, str(begin_p), end, "")  # 按日获取

    # 整理成二维表格，行为日期，列为股票代码，用于计算
    raw_df = pd.DataFrame(columns=data.Codes)
    for i in range(len(data.Codes)):
        raw_df[data.Codes[i] + 'old'] = pd.Series(data.Data[i])

    # 计算60日换手率标准差
    for code in data.Codes:
        raw_df[code] = raw_df[code + 'old'].rolling(win).std()  # 滚动
    raw_df = raw_df[data.Codes]
    raw_df['date'] = pd.Series(data.Times)  # 添加日期

    # 按周获取参照日期
    date_ref = w.tdays(begin, end, "Period={}".format(period))
    raw_df = raw_df[raw_df['date'].isin(date_ref.Times)]

    # 变形为三列，分别为股票代码、日期和因子值
    raw_df = raw_df.set_index("date")
    df = raw_df.stack().reset_index()
    df.rename(columns={ "level_1": "secID", 0: fac}, inplace=True)
    df["date"] = df["date"].apply(lambda x: x.strftime("%Y-%m-%d"))  # 转换日期为字符串格式
    return df


def bias_std_turn_1w(univ, begin, end, period):
    fac = sys._getframe().f_code.co_name  # 因子名称

    # 计算：(换手率标准差1w / 换手率标准差12w) - 1
    df1 = std_turn_1w(univ, begin, end, period)  # 调用相应函数
    df2 = std_turn_12w(univ, begin, end, period)
    df = pd.merge(df1, df2, on=['date', 'secID'])  # 合并
    df[fac] = df['std_turn_1w'] / df['std_turn_12w'] - 1

    # 保留三列
    #df = df[["secID", "date", fac]] 原来
    df = df[["date","secID", fac]]
    return df


def bias_std_turn_2w(univ, begin, end, period):
    fac = sys._getframe().f_code.co_name  # 因子名称

    # 计算：(换手率标准差2w / 换手率标准差12w) - 1
    df1 = std_turn_2w(univ, begin, end, period)  # 调用相应函数
    df2 = std_turn_12w(univ, begin, end, period)
    df = pd.merge(df1, df2, on=['date', 'secID'])  # 合并
    #原来
    #df[fac] = df['std_turn_1w'] / df['std_turn_12w'] - 1
    #修改
    df[fac] = df['std_turn_2w'] / df['std_turn_12w'] - 1
    # 保留三列
    #df = df[["secID", "date", fac]]
    df = df[["date", "secID", fac]]
    return df


def bias_std_turn_4w(univ, begin, end, period):
    fac = sys._getframe().f_code.co_name  # 因子名称

    # 计算：(换手率标准差4w / 换手率标准差12w) - 1
    df1 = std_turn_4w(univ, begin, end, period)  # 调用相应函数
    df2 = std_turn_12w(univ, begin, end, period)
    df = pd.merge(df1, df2, on=['date', 'secID'])  # 合并
    #原来
    #df[fac] = df['std_turn_1w'] / df['std_turn_12w'] - 1
    #修改
    df[fac] = df['std_turn_4w'] / df['std_turn_12w'] - 1

    # 保留三列
    #df = df[["secID", "date", fac]]
    df = df[["date", "secID", fac]]
    return df


# 动量
def weighted_strength_1w(univ, begin, end, period):
    fac = sys._getframe().f_code.co_name  # 因子名称
    wind_fac = ["turn", "pct_chg"]  # WIND因子名称
    win = 5  # 窗口
    # 获取开始时间的前5个交易日
    begin_p = w.tdaysoffset(-win, begin)
    begin_p = begin_p.Times[0]
    data_t = w.wsd(univ, wind_fac[0], str(begin_p), end, "")  # 按日获取
    data_r = w.wsd(univ, wind_fac[1], str(begin_p), end, "")

    # 整理成DataFrame，一共4列，分别是股票代码、日期和因子值(换手率和收益率)
    col_date = data_r.Times * len(data_r.Codes)
    col_code = [[i] * len(data_r.Times) for i in data_r.Codes]
    col_code = reduce(lambda x, y: x + y, col_code)
    col_fac_t = reduce(lambda x, y: x + y, data_t.Data)
    col_fac_r = reduce(lambda x, y: x + y, data_r.Data)
    df = pd.DataFrame({"secID": col_code, "date": col_date, "turn": col_fac_t, "pct_chg": col_fac_r})

    # 计算：sum(收益率*换手率)/sum(换手率)
    weight = df["turn"].groupby(df['secID']).rolling(win).sum()  # 分母：sum(换手率)，按股票分组滚动计算
    weight = weight.reset_index()
    df['prod'] = df["turn"] * df["pct_chg"]  # 收益率*换手率
    prod_sum = df['prod'].groupby(df['secID']).rolling(win).sum()  # 分子：sum(收益率*换手率)，按股票分组滚动计算
    prod_sum = prod_sum.reset_index()
    weight = pd.merge(weight, prod_sum, on=['secID', 'level_1'])  # 合并分子与分母
    weight[fac] = weight['prod'] / weight["turn"]  # 目标因子值
    weight['date'] = df['date']
    df = pd.merge(df, weight, how='left', on=['secID', 'date'])  # 合并股票代码、日期、因子值
    df = df[["secID", "date", fac]]

    # 按周获取参照日期
    date_ref = w.tdays(begin, end, "Period={}".format(period))
    df = df[df['date'].isin(date_ref.Times)]
    #df["date"].apply(lambda x: x.strftime("%Y-%m-%d"))  # 转换日期为字符串格式  原来
    df["date"] = df["date"].apply(lambda x: x.strftime("%Y-%m-%d"))

    return df


def weighted_strength_2w(univ, begin, end, period):
    fac = sys._getframe().f_code.co_name  # 因子名称
    wind_fac = ["turn", "pct_chg"]  # WIND因子名称
    win = 10  # 窗口
    # 获取开始时间的前10个交易日
    begin_p = w.tdaysoffset(-win, begin)
    begin_p = begin_p.Times[0]
    data_t = w.wsd(univ, wind_fac[0], str(begin_p), end, "")  # 按日获取
    data_r = w.wsd(univ, wind_fac[1], str(begin_p), end, "")

    # 整理成DataFrame，一共4列，分别是股票代码、日期和因子值(换手率和收益率)
    col_date = data_r.Times * len(data_r.Codes)
    col_code = [[i] * len(data_r.Times) for i in data_r.Codes]
    col_code = reduce(lambda x, y: x + y, col_code)
    col_fac_t = reduce(lambda x, y: x + y, data_t.Data)
    col_fac_r = reduce(lambda x, y: x + y, data_r.Data)
    df = pd.DataFrame({"secID": col_code, "date": col_date, "turn": col_fac_t, "pct_chg": col_fac_r})

    # 计算：sum(收益率*换手率)/sum(换手率)
    weight = df["turn"].groupby(df['secID']).rolling(win).sum()  # 分母：sum(换手率)，按股票分组滚动计算
    weight = weight.reset_index()
    df['prod'] = df["turn"] * df["pct_chg"]  # 收益率*换手率
    prod_sum = df['prod'].groupby(df['secID']).rolling(win).sum()  # 分子：sum(收益率*换手率)，按股票分组滚动计算
    prod_sum = prod_sum.reset_index()
    weight = pd.merge(weight, prod_sum, on=['secID', 'level_1'])  # 合并分子与分母
    weight[fac] = weight['prod'] / weight["turn"]  # 目标因子值
    weight['date'] = df['date']
    df = pd.merge(df, weight, how='left', on=['secID', 'date'])  # 合并股票代码、日期、因子值
    df = df[["secID", "date", fac]]

    # 按周获取参照日期
    date_ref = w.tdays(begin, end, "Period={}".format(period))
    df = df[df['date'].isin(date_ref.Times)]
    #df["date"].apply(lambda x: x.strftime("%Y-%m-%d"))  # 转换日期为字符串格式   原来
    df["date"] = df["date"].apply(lambda x: x.strftime("%Y-%m-%d"))
    return df


def weighted_strength_4w(univ, begin, end, period):
    fac = sys._getframe().f_code.co_name  # 因子名称
    wind_fac = ["turn", "pct_chg"]  # WIND因子名称
    win = 20  # 窗口
    # 获取开始时间的前20个交易日
    begin_p = w.tdaysoffset(-win, begin)
    begin_p = begin_p.Times[0]
    data_t = w.wsd(univ, wind_fac[0], str(begin_p), end, "")  # 按日获取
    data_r = w.wsd(univ, wind_fac[1], str(begin_p), end, "")

    # 整理成DataFrame，一共4列，分别是股票代码、日期和因子值(换手率和收益率)
    col_date = data_r.Times * len(data_r.Codes)
    col_code = [[i] * len(data_r.Times) for i in data_r.Codes]
    col_code = reduce(lambda x, y: x + y, col_code)
    col_fac_t = reduce(lambda x, y: x + y, data_t.Data)
    col_fac_r = reduce(lambda x, y: x + y, data_r.Data)
    df = pd.DataFrame({"secID": col_code, "date": col_date, "turn": col_fac_t, "pct_chg": col_fac_r})

    # 计算：sum(收益率*换手率)/sum(换手率)
    weight = df["turn"].groupby(df['secID']).rolling(win).sum()  # 分母：sum(换手率)，按股票分组滚动计算
    weight = weight.reset_index()
    df['prod'] = df["turn"] * df["pct_chg"]  # 收益率*换手率
    prod_sum = df['prod'].groupby(df['secID']).rolling(win).sum()  # 分子：sum(收益率*换手率)，按股票分组滚动计算
    prod_sum = prod_sum.reset_index()
    weight = pd.merge(weight, prod_sum, on=['secID', 'level_1'])  # 合并分子与分母
    weight[fac] = weight['prod'] / weight["turn"]  # 目标因子值
    weight['date'] = df['date']
    df = pd.merge(df, weight, how='left', on=['secID', 'date'])  # 合并股票代码、日期、因子值
    df = df[["secID", "date", fac]]

    # 按周获取参照日期
    date_ref = w.tdays(begin, end, "Period={}".format(period))
    df = df[df['date'].isin(date_ref.Times)]
    #df["date"].apply(lambda x: x.strftime("%Y-%m-%d"))  # 转换日期为字符串格式   原来
    df["date"] = df["date"].apply(lambda x: x.strftime("%Y-%m-%d"))

    return df


def weighted_strength_12w(univ, begin, end, period):
    fac = sys._getframe().f_code.co_name  # 因子名称
    wind_fac = ["turn", "pct_chg"]  # WIND因子名称
    win = 60  # 窗口
    # 获取开始时间的前60个交易日
    begin_p = w.tdaysoffset(-win, begin)
    begin_p = begin_p.Times[0]
    data_t = w.wsd(univ, wind_fac[0], str(begin_p), end, "")  # 按日获取
    data_r = w.wsd(univ, wind_fac[1], str(begin_p), end, "")

    # 整理成DataFrame，一共4列，分别是股票代码、日期和因子值(换手率和收益率)
    col_date = data_r.Times * len(data_r.Codes)
    col_code = [[i] * len(data_r.Times) for i in data_r.Codes]
    col_code = reduce(lambda x, y: x + y, col_code)
    col_fac_t = reduce(lambda x, y: x + y, data_t.Data)
    col_fac_r = reduce(lambda x, y: x + y, data_r.Data)
    df = pd.DataFrame({"secID": col_code, "date": col_date, "turn": col_fac_t, "pct_chg": col_fac_r})

    # 计算：sum(收益率*换手率)/sum(换手率)
    weight = df["turn"].groupby(df['secID']).rolling(win).sum()  # 分母：sum(换手率)，按股票分组滚动计算
    weight = weight.reset_index()
    df['prod'] = df["turn"] * df["pct_chg"]  # 收益率*换手率
    prod_sum = df['prod'].groupby(df['secID']).rolling(win).sum()  # 分子：sum(收益率*换手率)，按股票分组滚动计算
    prod_sum = prod_sum.reset_index()
    weight = pd.merge(weight, prod_sum, on=['secID', 'level_1'])  # 合并分子与分母
    weight[fac] = weight['prod'] / weight["turn"]  # 目标因子值
    weight['date'] = df['date']
    df = pd.merge(df, weight, how='left', on=['secID', 'date'])  # 合并股票代码、日期、因子值
    df = df[["secID", "date", fac]]

    # 按周获取参照日期
    date_ref = w.tdays(begin, end, "Period={}".format(period))
    df = df[df['date'].isin(date_ref.Times)]
    #df["date"].apply(lambda x: x.strftime("%Y-%m-%d"))  # 转换日期为字符串格式   原来
    df["date"] = df["date"].apply(lambda x: x.strftime("%Y-%m-%d"))
    return df


def wtd_sum(nums, order):
    '''加权求和'''
    return sum([nums[i] * order[i] for i in range(len(nums))])


def exp_wgt_return_1w(univ, begin, end, period):
    fac = sys._getframe().f_code.co_name  # 因子名称
    wind_fac = ["turn", "pct_chg"]  # WIND因子名称
    win = 5  # 窗口
    # 获取开始时间的前5个交易日
    begin_p = w.tdaysoffset(-win, begin)
    begin_p = begin_p.Times[0]
    data_t = w.wsd(univ, wind_fac[0], str(begin_p), end, "")  # 按日获取
    data_r = w.wsd(univ, wind_fac[1], str(begin_p), end, "")

    # 整理成DataFrame，一共4列，分别是股票代码、日期和因子值(换手率和收益率)
    col_date = data_r.Times * len(data_r.Codes)
    col_code = [[i] * len(data_r.Times) for i in data_r.Codes]
    col_code = reduce(lambda x, y: x + y, col_code)
    col_fac_t = reduce(lambda x, y: x + y, data_t.Data)
    col_fac_r = reduce(lambda x, y: x + y, data_r.Data)
    df = pd.DataFrame({"secID": col_code, "date": col_date, "turn": col_fac_t, "pct_chg": col_fac_r})

    # 计算：sum(收益率*换手率*指数系数)/sum(换手率*指数系数)
    coef = [math.exp(-j / 4 / (win / 5)) for j in range(win - 1, -1, -1)]  # 指数系数exp(-x/4N)，x为距离当前日期天数，N为周数
    weight = df["turn"].groupby(df['secID']).rolling(win).apply(wtd_sum, args=(coef,))  # 分母：sum(换手率*指数系数)
    weight = weight.reset_index()
    df['prod'] = df["turn"] * df["pct_chg"]  # 收益率*换手率
    prod_sum = df['prod'].groupby(df['secID']).rolling(win).apply(wtd_sum, args=(coef,))  # 分子：sum(收益率*换手率*指数系数)
    prod_sum = prod_sum.reset_index()
    weight = pd.merge(weight, prod_sum, on=['secID', 'level_1'])  # 合并分子与分母
    weight[fac] = weight['prod'] / weight["turn"]  # 分子/分母
    weight['date'] = df['date']
    df = pd.merge(df, weight, how='left', on=['secID', 'date'])  # 合并股票代码、日期、因子值
    df = df[["secID", "date", fac]]

    # 按周获取参照日期
    date_ref = w.tdays(begin, end, "Period={}".format(period))
    df = df[df['date'].isin(date_ref.Times)]
    #df["date"].apply(lambda x: x.strftime("%Y-%m-%d"))  # 转换日期为字符串格式  原来
    df["date"] = df["date"].apply(lambda x: x.strftime("%Y-%m-%d"))

    return df


def exp_wgt_return_2w(univ, begin, end, period):
    fac = sys._getframe().f_code.co_name  # 因子名称
    wind_fac = ["turn", "pct_chg"]  # WIND因子名称
    win = 10  # 窗口
    # 获取开始时间的前10个交易日
    begin_p = w.tdaysoffset(-win, begin)
    begin_p = begin_p.Times[0]
    data_t = w.wsd(univ, wind_fac[0], str(begin_p), end, "")  # 按日获取
    data_r = w.wsd(univ, wind_fac[1], str(begin_p), end, "")

    # 整理成DataFrame，一共4列，分别是股票代码、日期和因子值(换手率和收益率)
    col_date = data_r.Times * len(data_r.Codes)
    col_code = [[i] * len(data_r.Times) for i in data_r.Codes]
    col_code = reduce(lambda x, y: x + y, col_code)
    col_fac_t = reduce(lambda x, y: x + y, data_t.Data)
    col_fac_r = reduce(lambda x, y: x + y, data_r.Data)
    df = pd.DataFrame({"secID": col_code, "date": col_date, "turn": col_fac_t, "pct_chg": col_fac_r})

    # 计算：sum(收益率*换手率*指数系数)/sum(换手率*指数系数)
    coef = [math.exp(-j / 4 / (win / 5)) for j in range(win - 1, -1, -1)]  # 指数系数exp(-x/4N)，x为距离当前日期天数，N为周数
    weight = df["turn"].groupby(df['secID']).rolling(win).apply(wtd_sum, args=(coef,))  # 分母：sum(换手率*指数系数)
    weight = weight.reset_index()
    df['prod'] = df["turn"] * df["pct_chg"]  # 收益率*换手率
    prod_sum = df['prod'].groupby(df['secID']).rolling(win).apply(wtd_sum, args=(coef,))  # 分子：sum(收益率*换手率*指数系数)
    prod_sum = prod_sum.reset_index()
    weight = pd.merge(weight, prod_sum, on=['secID', 'level_1'])  # 合并分子与分母
    weight[fac] = weight['prod'] / weight["turn"]  # 分子/分母
    weight['date'] = df['date']
    df = pd.merge(df, weight, how='left', on=['secID', 'date'])  # 合并股票代码、日期、因子值
    df = df[["secID", "date", fac]]

    # 按周获取参照日期
    date_ref = w.tdays(begin, end, "Period={}".format(period))
    df = df[df['date'].isin(date_ref.Times)]
    #df["date"].apply(lambda x: x.strftime("%Y-%m-%d"))  # 转换日期为字符串格式   原来
    df["date"] = df["date"].apply(lambda x: x.strftime("%Y-%m-%d"))
    return df


def exp_wgt_return_4w(univ, begin, end, period):
    fac = sys._getframe().f_code.co_name  # 因子名称
    wind_fac = ["turn", "pct_chg"]  # WIND因子名称
    win = 20  # 窗口
    # 获取开始时间的前20个交易日
    begin_p = w.tdaysoffset(-win, begin)
    begin_p = begin_p.Times[0]
    data_t = w.wsd(univ, wind_fac[0], str(begin_p), end, "")  # 按日获取
    data_r = w.wsd(univ, wind_fac[1], str(begin_p), end, "")

    # 整理成DataFrame，一共4列，分别是股票代码、日期和因子值(换手率和收益率)
    col_date = data_r.Times * len(data_r.Codes)
    col_code = [[i] * len(data_r.Times) for i in data_r.Codes]
    col_code = reduce(lambda x, y: x + y, col_code)
    col_fac_t = reduce(lambda x, y: x + y, data_t.Data)
    col_fac_r = reduce(lambda x, y: x + y, data_r.Data)
    df = pd.DataFrame({"secID": col_code, "date": col_date, "turn": col_fac_t, "pct_chg": col_fac_r})

    # 计算：sum(收益率*换手率*指数系数)/sum(换手率*指数系数)
    coef = [math.exp(-j / 4 / (win / 5)) for j in range(win - 1, -1, -1)]  # 指数系数exp(-x/4N)，x为距离当前日期天数，N为周数
    weight = df["turn"].groupby(df['secID']).rolling(win).apply(wtd_sum, args=(coef,))  # 分母：sum(换手率*指数系数)
    weight = weight.reset_index()
    df['prod'] = df["turn"] * df["pct_chg"]  # 收益率*换手率
    prod_sum = df['prod'].groupby(df['secID']).rolling(win).apply(wtd_sum, args=(coef,))  # 分子：sum(收益率*换手率*指数系数)
    prod_sum = prod_sum.reset_index()
    weight = pd.merge(weight, prod_sum, on=['secID', 'level_1'])  # 合并分子与分母
    weight[fac] = weight['prod'] / weight["turn"]  # 分子/分母
    weight['date'] = df['date']
    df = pd.merge(df, weight, how='left', on=['secID', 'date'])  # 合并股票代码、日期、因子值
    df = df[["secID", "date", fac]]

    # 按周获取参照日期
    date_ref = w.tdays(begin, end, "Period={}".format(period))
    df = df[df['date'].isin(date_ref.Times)]
    #df["date"].apply(lambda x: x.strftime("%Y-%m-%d"))  # 转换日期为字符串格式   原来
    df["date"] = df["date"].apply(lambda x: x.strftime("%Y-%m-%d"))
    return df


def exp_wgt_return_12w(univ, begin, end, period):
    fac = sys._getframe().f_code.co_name  # 因子名称
    wind_fac = ["turn", "pct_chg"]  # WIND因子名称
    win = 60  # 窗口
    # 获取开始时间的前60个交易日
    begin_p = w.tdaysoffset(-win, begin)
    begin_p = begin_p.Times[0]
    data_t = w.wsd(univ, wind_fac[0], str(begin_p), end, "")  # 按日获取
    data_r = w.wsd(univ, wind_fac[1], str(begin_p), end, "")

    # 整理成DataFrame，一共4列，分别是股票代码、日期和因子值(换手率和收益率)
    col_date = data_r.Times * len(data_r.Codes)
    col_code = [[i] * len(data_r.Times) for i in data_r.Codes]
    col_code = reduce(lambda x, y: x + y, col_code)
    col_fac_t = reduce(lambda x, y: x + y, data_t.Data)
    col_fac_r = reduce(lambda x, y: x + y, data_r.Data)
    df = pd.DataFrame({"secID": col_code, "date": col_date, "turn": col_fac_t, "pct_chg": col_fac_r})

    # 计算：sum(收益率*换手率*指数系数)/sum(换手率*指数系数)
    coef = [math.exp(-j / 4 / (win / 5)) for j in range(win - 1, -1, -1)]  # 指数系数exp(-x/4N)，x为距离当前日期天数，N为周数
    weight = df["turn"].groupby(df['secID']).rolling(win).apply(wtd_sum, args=(coef,))  # 分母：sum(换手率*指数系数)
    weight = weight.reset_index()
    df['prod'] = df["turn"] * df["pct_chg"]  # 收益率*换手率
    prod_sum = df['prod'].groupby(df['secID']).rolling(win).apply(wtd_sum, args=(coef,))  # 分子：sum(收益率*换手率*指数系数)
    prod_sum = prod_sum.reset_index()
    weight = pd.merge(weight, prod_sum, on=['secID', 'level_1'])  # 合并分子与分母
    weight[fac] = weight['prod'] / weight["turn"]  # 分子/分母
    weight['date'] = df['date']
    df = pd.merge(df, weight, how='left', on=['secID', 'date'])  # 合并股票代码、日期、因子值
    df = df[["secID", "date", fac]]

    # 按周获取参照日期
    date_ref = w.tdays(begin, end, "Period={}".format(period))
    df = df[df['date'].isin(date_ref.Times)]
    #df["date"].apply(lambda x: x.strftime("%Y-%m-%d"))  # 转换日期为字符串格式    原来
    df["date"] = df["date"].apply(lambda x: x.strftime("%Y-%m-%d"))
    return df


def HAlpha(univ, begin, end, period):
    fac = sys._getframe().f_code.co_name  # 因子名称：过去100天收益向上证综指和常数回归结果中的常数系数
    win = 100  # 窗口
    # 获取开始时间的前1000个交易日
    begin_p = w.tdaysoffset(-win, begin)
    begin_p = begin_p.Times[0]
    wind_fac = "pct_chg"  # WIND因子名称
    data_y = w.wsd(univ, wind_fac, str(begin_p), end, "")  # 按日获取
    benchmark = "000001.SH"  # 自变量为上证综指
    data_x = w.wsd(benchmark, wind_fac, str(begin_p), end, "")  # 获取自变量数据

    # 因变量：整理成二维表格，行为日期，列为股票代码
    df_y = pd.DataFrame(columns=data_y.Codes)
    for i in range(len(data_y.Codes)):
        df_y[data_y.Codes[i]] = pd.Series(data_y.Data[i])
    df_y["date"] = pd.Series(data_y.Times)
    # 自变量
    df_x = pd.DataFrame({"date": data_x.Times, "bck": data_x.Data[0]})
    # 合并自变量与因变量
    raw_df = pd.merge(df_y, df_x, on="date")
    raw_df["const"] = 1  # 添加常数

    # 回归各股票与上证综指，形成二维表格，行为日期，列为股票代码
    result = {}  # 字典，键为股票代码，值为回归结果
    for code in data_y.Codes:
        result[code] = []
        for i in range(win, len(raw_df) + 1):  # 从第100开始循环
            x = raw_df.loc[i - win:i, ["bck", "const"]]  # 截取自变量
            y = raw_df.loc[i - win:i, code]  # 截取因变量
            est = sm.OLS(y, x)
            result[code].append(est.fit().params["const"])  # 添加结果
    df = pd.DataFrame(result)
    # 添加日期
    dt = raw_df.loc[win - 1:len(raw_df), "date"]
    dt.index = pd.Series(range(len(dt)))
    df['date'] = dt

    # 按周获取参照日期
    date_ref = w.tdays(begin, end, "Period={}".format(period))
    df = df[df['date'].isin(date_ref.Times)]

    # 变形为三列，分别为股票代码、日期和因子值
    df = df.set_index("date")
    df = df.stack().reset_index()
    df.rename(columns={"level_1": "secID", "level_0": "date", 0: fac}, inplace=True)
    #df["date"].apply(lambda x: x.strftime("%Y-%m-%d"))  # 转换日期为字符串格式  原来
    df["date"] = df["date"].apply(lambda x: x.strftime("%Y-%m-%d"))
    return df


# 波动率（问题代码）
def beta_consistence(univ, begin, end, period):
    fac = sys._getframe().f_code.co_name  # 因子名称：过去100天收益向上证综指和常数回归结果中贝塔与残差标准差的乘积
    win = 100  # 窗口
    # 获取开始时间的前100个交易日
    begin_p = w.tdaysoffset(-win, begin)
    begin_p = begin_p.Times[0]
    wind_fac = "pct_chg"  # WIND因子名称
    data_y = w.wsd(univ, wind_fac, str(begin_p), end, "")  # 按日获取
    benchmark = "000001.SH"  # 自变量为上证综指
    data_x = w.wsd(benchmark, wind_fac, str(begin_p), end, "")  # 获取自变量数据

    # 因变量：整理成二维表格，行为日期，列为股票代码
    df_y = pd.DataFrame(columns=data_y.Codes)
    for i in range(len(data_y.Codes)):
        df_y[data_y.Codes[i]] = pd.Series(data_y.Data[i])
    df_y["date"] = pd.Series(data_y.Times)
    # 自变量
    df_x = pd.DataFrame({"date": data_x.Times, "bck": data_x.Data[0]})
    # 合并自变量与因变量
    raw_df = pd.merge(df_y, df_x, on="date")
    raw_df["const"] = 1  # 添加常数

    # 回归各股票与上证综指，形成二维表格，行为日期，列为股票代码
    result = {}  # 字典，键为股票代码，值为回归结果
    for code in data_y.Codes:
        result[code] = []
        for i in range(win, len(raw_df) + 1):  # 从第100开始循环
            x = raw_df.loc[i - win:i, ["bck", "const"]]  # 截取自变量
            y = raw_df.loc[i - win:i, code]  # 截取因变量
            est = sm.OLS(y, x)
            beta = est.fit().params["bck"]
            resid_std = est.fit().resid.std()
            result[code].append(beta * resid_std)  # 添加结果
    df = pd.DataFrame(result)
    # 添加日期
    dt = raw_df.loc[win - 1:len(raw_df), "date"]
    dt.index = pd.Series(range(len(dt)))
    df['date'] = dt

    # 按周获取参照日期
    date_ref = w.tdays(begin, end, "Period={}".format(period))
    df = df[df['date'].isin(date_ref.Times)]

    # 变形为三列，分别为股票代码、日期和因子值
    df = df.set_index("date")
    df = df.stack().reset_index()
    df.rename(columns={"level_0": "date","level_1": "secID",  0: fac}, inplace=True)
    #df["date"].apply(lambda x: x.strftime("%Y-%m-%d"))  # 转换日期为字符串格式   原来
    #df["secID"] = sorted(df["secID"])
    df["date"] = df["date"].apply(lambda x: x.strftime("%Y-%m-%d"))
    return df


def id1_std_3m(univ, begin, end, period):
    fac = sys._getframe().f_code.co_name  # 因子名称：过去60天收益向上证综指和常数回归结果中残差标准差
    win = 60  # 窗口
    # 获取开始时间的前60个交易日
    begin_p = w.tdaysoffset(-win, begin)
    begin_p = begin_p.Times[0]
    wind_fac = "pct_chg"  # WIND因子名称
    data_y = w.wsd(univ, wind_fac, str(begin_p), end, "")  # 按日获取
    benchmark = "000001.SH"  # 自变量为上证综指
    data_x = w.wsd(benchmark, wind_fac, str(begin_p), end, "")  # 获取自变量数据

    # 因变量：整理成二维表格，行为日期，列为股票代码
    df_y = pd.DataFrame(columns=data_y.Codes)
    for i in range(len(data_y.Codes)):
        df_y[data_y.Codes[i]] = pd.Series(data_y.Data[i])
    df_y["date"] = pd.Series(data_y.Times)
    # 自变量
    df_x = pd.DataFrame({"date": data_x.Times, "bck": data_x.Data[0]})
    # 合并自变量与因变量
    raw_df = pd.merge(df_y, df_x, on="date")
    raw_df["const"] = 1  # 添加常数

    # 回归各股票与上证综指，形成二维表格，行为日期，列为股票代码
    result = {}  # 字典，键为股票代码，值为回归结果
    for code in data_y.Codes:
        result[code] = []
        for i in range(win, len(raw_df) + 1):  # 从第60开始循环
            x = raw_df.loc[i - win:i, ["bck", "const"]]  # 截取自变量
            y = raw_df.loc[i - win:i, code]  # 截取因变量
            est = sm.OLS(y, x)
            resid_std = est.fit().resid.std()
            result[code].append(resid_std)  # 添加结果
    df = pd.DataFrame(result)
    # 添加日期
    dt = raw_df.loc[win - 1:len(raw_df), "date"]
    dt.index = pd.Series(range(len(dt)))
    df['date'] = dt

    # 按周获取参照日期
    date_ref = w.tdays(begin, end, "Period={}".format(period))
    df = df[df['date'].isin(date_ref.Times)]

    # 变形为三列，分别为股票代码、日期和因子值
    df = df.set_index("date")
    df = df.stack().reset_index()
    df.rename(columns={"level_0": "date","level_1": "secID", 0: fac}, inplace=True)
    #df["date"].apply(lambda x: x.strftime("%Y-%m-%d"))  # 转换日期为字符串格式  原来
    #df["secID"] = sorted(df["secID"])
    df["date"] = df["date"].apply(lambda x: x.strftime("%Y-%m-%d"))
    return df


def MVF(begin, end):
    '''计算规模因子日收益率：按前一日规模大小对A股所有股票排序，取后30%的股票平均日收益减去前30%股票平均日收益，得到的结果作为今天的值'''
    # 获取开始时间的前一交易日
    begin_p = w.tdaysoffset(-1, begin)
    begin_p = begin_p.Times[0]
    # 获取交易日历：从开始时间前一交易日到截止时间
    calendar = w.tdays(str(begin_p), end, "")
    date_list = calendar.Times

    mvf = []  # 列表用于存放市值因子日收益率
    data, mv = {}, {}  # 字典用于存放不同日期的市值数据，分别WindData和Series类型
    # 按交易日历每日循环
    for i in range(len(date_list) - 1):
        # 获取对应日期A股代码
        stk_list = w.wset("sectorconstituent", "date={};sectorid=a001010100000000".format(str(date_list[i])))
        stk_list = stk_list.Data[1]
        # 获取并存放市值数据
        data[date_list[i + 1]] = w.wss(stk_list, "mkt_cap_ard", "unit=1;tradeDate={}".format(str(date_list[i])))
        mv[date_list[i + 1]] = pd.Series(data[date_list[i + 1]].Data[0], index=stk_list)
        # 删去空值并排序
        mv[date_list[i + 1]].dropna(inplace=True)
        mv[date_list[i + 1]].sort_values(inplace=True)
        # 确定前后30%股票数量
        num = round(len(stk_list) * 0.3)
        # 分别获取对应股票的收益率
        small, large = list(mv[date_list[i + 1]].index[:num]), list(mv[date_list[i + 1]].index[-num:])
        large_data = w.wss(large, "pct_chg", "unit=1;tradeDate={}".format(str(date_list[i + 1])))
        small_data = w.wss(small, "pct_chg", "unit=1;tradeDate={}".format(str(date_list[i + 1])))
        # 计算因子日收益率
        mvf.append(np.nanmean(small_data.Data[0]) - np.nanmean(large_data.Data[0]))

    # 两列：日期和规模因子日收益率
    mvf = pd.DataFrame({"date": date_list[1:], "mvf": mvf})
    return mvf


def PBF(begin, end):
    '''计算BP因子日收益率：按前一日PB大小对A股所有股票排序，取后30%的股票平均日收益减去前30%股票平均日收益，得到的结果作为今天的值'''
    # 获取开始时间的前一交易日
    begin_p = w.tdaysoffset(-1, begin)
    begin_p = begin_p.Times[0]
    # 获取交易日历：从开始时间前一交易日到截止时间
    calendar = w.tdays(str(begin_p), end, "")
    date_list = calendar.Times

    pbf = []  # 列表用于存放BP因子日收益率
    data, pb = {}, {}  # 字典用于存放不同日期的PB数据，分别WindData和Series类型
    # 按交易日历每日循环
    for i in range(len(date_list) - 1):
        # 获取对应日期A股代码
        stk_list = w.wset("sectorconstituent", "date={};sectorid=a001010100000000".format(str(date_list[i])))
        stk_list = stk_list.Data[1]
        # 获取并存放市值数据
        data[date_list[i + 1]] = w.wss(stk_list, "pb_lf", "unit=1;tradeDate={}".format(str(date_list[i])))
        pb[date_list[i + 1]] = pd.Series(data[date_list[i + 1]].Data[0], index=stk_list)
        # 删去空值并排序
        pb[date_list[i + 1]].dropna(inplace=True)
        pb[date_list[i + 1]].sort_values(inplace=True)
        # 确定前后30%股票数量
        num = round(len(stk_list) * 0.3)
        # 分别获取对应股票的收益率
        small, large = list(pb[date_list[i + 1]].index[:num]), list(pb[date_list[i + 1]].index[-num:])
        large_data = w.wss(large, "pct_chg", "unit=1;tradeDate={}".format(str(date_list[i + 1])))
        small_data = w.wss(small, "pct_chg", "unit=1;tradeDate={}".format(str(date_list[i + 1])))
        # 计算因子日收益率
        pbf.append(np.nanmean(small_data.Data[0]) - np.nanmean(large_data.Data[0]))
    # 两列：日期和BP因子日收益率
    pbf = pd.DataFrame({"date": date_list[1:], "pbf": pbf})
    return pbf


def id2_std_3m(univ, begin, end, period):
    fac = sys._getframe().f_code.co_name  # 因子名称：过去60天收益向中证全指、规模因子日收益率、BP因子日收益率回归结果中残差标准差
    win = 60  # 窗口
    # 获取开始时间的前60个交易日
    begin_p = w.tdaysoffset(-win, begin)
    begin_p = begin_p.Times[0]
    wind_fac = ["pct_chg"]  # WIND因子名称
    data_y = w.wsd(univ, wind_fac, str(begin_p), end, "")  # 按日获取
    benchmark = "000985.SH"  # 自变量为中证全指
    data_bck = w.wsd(benchmark, wind_fac, str(begin_p), end, "")  # 获取自变量数据

    # 因变量：整理成二维表格，行为日期，列为股票代码
    df_y = pd.DataFrame(columns=data_y.Codes)
    for i in range(len(data_y.Codes)):
        df_y[data_y.Codes[i]] = pd.Series(data_y.Data[i])
    df_y["date"] = pd.Series(data_y.Times)
    # 自变量
    df_x = pd.DataFrame({"date": data_bck.Times, "bck": data_bck.Data[0]})
    mvf = MVF(begin, end)
    pbf = PBF(begin, end)
    # 合并自变量与因变量
    #raw_df = pd.merge(df_y, df_x, mvf, pbf, on="date") #原来
    #修改
    raw_df1 = pd.merge(df_y, df_x,on="date")
    raw_df2 = pd.merge(mvf, pbf, on="date")
    df = pd.merge(raw_df1, raw_df2,on="date")

    # 按周获取参照日期
    date_ref = w.tdays(begin, end, "Period={}".format(period))
    df = df[df['date'].isin(date_ref.Times)]

    # 变形为三列，分别为股票代码、日期和因子值
    df = df.set_index("date")
    df = df.stack().reset_index()
    df.rename(columns={ "level_0": "date","level_1": "secID", 0: fac}, inplace=True)
    #df["secID"] = sorted(df["secID"])
    #df["date"].apply(lambda x: x.strftime("%Y-%m-%d"))  # 转换日期为字符串格式
    df["date"] = df["date"].apply(lambda x: x.strftime("%Y-%m-%d"))
    return df


def id2_std_up_3m(univ, begin, end, period):
    fac = sys._getframe().f_code.co_name  # 因子名称：过去60天收益向中证全指、规模因子日收益率、BP因子日收益率回归结果中上行波动率
    win = 60  # 窗口
    # 获取开始时间的前60个交易日
    begin_p = w.tdaysoffset(-win, begin)
    begin_p = begin_p.Times[0]
    wind_fac = ["pct_chg"]  # WIND因子名称
    data_y = w.wsd(univ, wind_fac, str(begin_p), end, "")  # 按日获取
    benchmark = "000985.SH"  # 自变量为中证全指
    data_bck = w.wsd(benchmark, wind_fac, str(begin_p), end, "")  # 获取自变量数据

    # 因变量：整理成二维表格，行为日期，列为股票代码
    df_y = pd.DataFrame(columns=data_y.Codes)
    for i in range(len(data_y.Codes)):
        df_y[data_y.Codes[i]] = pd.Series(data_y.Data[i])
    df_y["date"] = pd.Series(data_y.Times)
    # 自变量
    df_x = pd.DataFrame({"date": data_bck.Times, "bck": data_bck.Data[0]})
    # 合并自变量与因变量
    mvf = MVF(begin, end)
    pbf = PBF(begin, end)
    raw_df1 = pd.merge(df_y, df_x, on="date")
    raw_df2 = pd.merge(mvf, pbf, on="date")
    df = pd.merge(raw_df1, raw_df2, on="date")
    # 按周获取参照日期
    date_ref = w.tdays(begin, end, "Period={}".format(period))
    df = df[df['date'].isin(date_ref.Times)]

    # 变形为三列，分别为股票代码、日期和因子值
    df = df.set_index("date")
    df = df.stack().reset_index()
    df.rename(columns={"level_1": "secID", "level_0": "date", 0: fac}, inplace=True)
    #df["date"].apply(lambda x: x.strftime("%Y-%m-%d"))  # 转换日期为字符串格式  原来
    df["date"] = df["date"].apply(lambda x: x.strftime("%Y-%m-%d"))
    return df


def id2_std_down_3m(univ, begin, end, period):
    fac = sys._getframe().f_code.co_name  # 因子名称：过去60天收益向中证全指、规模因子日收益率、BP因子日收益率回归结果中下行波动率
    win = 60  # 窗口
    # 获取开始时间的前60个交易日
    begin_p = w.tdaysoffset(-win, begin)
    begin_p = begin_p.Times[0]
    wind_fac = ["pct_chg"]  # WIND因子名称
    data_y = w.wsd(univ, wind_fac, str(begin_p), end, "")  # 按日获取
    benchmark = "000985.SH"  # 自变量为中证全指
    data_bck = w.wsd(benchmark, wind_fac, str(begin_p), end, "")  # 获取自变量数据

    # 因变量：整理成二维表格，行为日期，列为股票代码
    df_y = pd.DataFrame(columns=data_y.Codes)
    for i in range(len(data_y.Codes)):
        df_y[data_y.Codes[i]] = pd.Series(data_y.Data[i])
    df_y["date"] = pd.Series(data_y.Times)
    # 自变量
    df_x = pd.DataFrame({"date": data_bck.Times, "bck": data_bck.Data[0]})
    # 合并自变量与因变量
    mvf = MVF(begin, end)
    pbf = PBF(begin, end)
    raw_df1 = pd.merge(df_y, df_x, on="date")
    raw_df2 = pd.merge(mvf, pbf, on="date")
    df = pd.merge(raw_df1, raw_df2, on="date")
    # 按周获取参照日期
    date_ref = w.tdays(begin, end, "Period={}".format(period))
    df = df[df['date'].isin(date_ref.Times)]

    # 变形为三列，分别为股票代码、日期和因子值
    df = df.set_index("date")
    df = df.stack().reset_index()
    df.rename(columns={"level_1": "secID", "level_0": "date", 0: fac}, inplace=True)
    #df["date"].apply(lambda x: x.strftime("%Y-%m-%d"))  # 转换日期为字符串格式  原来
    df["date"] = df["date"].apply(lambda x: x.strftime("%Y-%m-%d"))
    return df

def high_r_std_3m(univ, begin, end, period):
    fac = sys._getframe().f_code.co_name  # 因子名称
    wind_fac = ["high", "pre_close"]
    win = 60  # 窗口
    # 获取开始时间的前60个交易日
    begin_p = w.tdaysoffset(-win, begin)
    begin_p = begin_p.Times[0]
    data = dict()
    data[wind_fac[0]] = w.wsd(univ, wind_fac[0], str(begin_p), end, "PriceAdj=F")  # 按日获取并且前复权
    data[wind_fac[1]] = w.wsd(univ, wind_fac[1], str(begin_p), end, "PriceAdj=F")  # 按日获取并且前复权

    # 整理成DataFrame，按列分别是股票代码、日期和待计算因子值
    col_date = data[wind_fac[0]].Times * len(data[wind_fac[0]].Codes)
    col_code = [[i] * len(data[wind_fac[0]].Times) for i in data[wind_fac[0]].Codes]
    col_code = reduce(lambda x, y: x + y, col_code)
    raw_df = pd.DataFrame({"secID": col_code, "date": col_date})
    for i in wind_fac:  # 按列添加待计算因子值
        col_fac = reduce(lambda x, y: x + y, data[i].Data)
        raw_df[i] = pd.Series(col_fac)

    # 计算因子值
    raw_df[fac] = raw_df["high"] / raw_df["pre_close"]  # 计算幅度，当日最高价/前一日收盘价
    df = raw_df[fac].groupby(raw_df["secID"]).rolling(win).std()  # 滚动计算标准差
    df = df.reset_index()
    df["date"] = raw_df["date"]  # 添加日期
    df = df[["secID", "date", fac]]

    # 按周获取参照日期
    date_ref = w.tdays(begin, end, "Period={}".format(period))
    df = df[df['date'].isin(date_ref.Times)]
    #df["date"].apply(lambda x: x.strftime("%Y-%m-%d"))  # 转换日期为字符串格式  原来
    df["date"] = df["date"].apply(lambda x: x.strftime("%Y-%m-%d"))
    return df


def low_r_std_3m(univ, begin, end, period):
    fac = sys._getframe().f_code.co_name  # 因子名称
    wind_fac = ["low", "pre_close"]
    win = 60  # 窗口
    # 获取开始时间的前60个交易日
    begin_p = w.tdaysoffset(-win, begin)
    begin_p = begin_p.Times[0]
    data = dict()
    data[wind_fac[0]] = w.wsd(univ, wind_fac[0], str(begin_p), end, "PriceAdj=F")  # 按日获取并且前复权
    data[wind_fac[1]] = w.wsd(univ, wind_fac[1], str(begin_p), end, "PriceAdj=F")  # 按日获取并且前复权

    # 整理成DataFrame，按列分别是股票代码、日期和待计算因子值
    col_date = data[wind_fac[0]].Times * len(data[wind_fac[0]].Codes)
    col_code = [[i] * len(data[wind_fac[0]].Times) for i in data[wind_fac[0]].Codes]
    col_code = reduce(lambda x, y: x + y, col_code)
    raw_df = pd.DataFrame({"secID": col_code, "date": col_date})
    for i in wind_fac:  # 按列添加待计算因子值
        col_fac = reduce(lambda x, y: x + y, data[i].Data)
        raw_df[i] = pd.Series(col_fac)

    # 计算因子值
    raw_df[fac] = raw_df["low"] / raw_df["pre_close"]  # 计算幅度，当日最低价/前一日收盘价
    df = raw_df[fac].groupby(raw_df["secID"]).rolling(win).std()  # 滚动计算标准差
    df = df.reset_index()
    df["date"] = raw_df["date"]  # 添加日期
    df = df[["secID", "date", fac]]

    # 按周获取参照日期
    date_ref = w.tdays(begin, end, "Period={}".format(period))
    df = df[df['date'].isin(date_ref.Times)]
    #df["date"].apply(lambda x: x.strftime("%Y-%m-%d"))  # 转换日期为字符串格式  原来
    df["date"] = df["date"].apply(lambda x: x.strftime("%Y-%m-%d"))
    return df


def hml_r_std_3m(univ, begin, end, period):
    fac = sys._getframe().f_code.co_name  # 因子名称

    # 获取上行和下行波动率
    high_vol = high_r_std_3m(univ, begin, end, period)
    low_vol = low_r_std_3m(univ, begin, end, period)
    df = pd.merge(high_vol, low_vol, on=["secID", "date"])  # 合并
    df[fac] = df["high_r_std_3m"] - df["low_r_std_3m"]  # 两者相减

    # 保留三列
    df = df[["secID", "date", fac]]
    return df


def hpl_r_std_3m(univ, begin, end, period):
    fac = sys._getframe().f_code.co_name  # 因子名称

    # 获取上行和下行波动率
    high_vol = high_r_std_3m(univ, begin, end, period)
    low_vol = low_r_std_3m(univ, begin, end, period)
    df = pd.merge(high_vol, low_vol, on=["secID", "date"])  # 合并
    df[fac] = df["high_r_std_3m"] + df["low_r_std_3m"]  # 两者相减

    # 保留三列
    df = df[["secID", "date", fac]]
    return df


# 杠杆（财务数据缺失）
def financial_leverage(univ, begin, end, period):
    fac = sys._getframe().f_code.co_name  # 因子名称
    # 数据取自财务报告
    wind_fac = ["tot_assets", "tot_equity", "other_equity_instruments_PRE"]
    # 由于财务数据为经常缺失，所以每次获取数据从上一年开始，这样空缺值可以按上一个值填充，若仍为空值则不作修改
    year = int(begin[:4])
    year_pre = year - 1
    begin_p = str(year_pre) + "-12-25"
    # 获取数据
    data = dict()
    for i in wind_fac:
        data[i] = w.wsd(univ, i, begin_p, end, "unit=1;rptType=1;Period={};Fill=Previous".format(period))

    # 整理成DataFrame，按列分别是股票代码、日期和待计算因子值
    col_date = data[wind_fac[0]].Times * len(data[wind_fac[0]].Codes)
    col_code = [[i] * len(data[wind_fac[0]].Times) for i in data[wind_fac[0]].Codes]
    col_code = reduce(lambda x, y: x + y, col_code)
    df = pd.DataFrame({"secID": col_code, "date": col_date})
    for i in wind_fac:  # 按列添加待计算因子值
        col_fac = reduce(lambda x, y: x + y, data[i].Data)
        df[i] = pd.Series(col_fac)

    # 计算因子值：（资产合计/(所有者权益-优先股权益)）
    df[fac] = df["tot_assets"] / (df["tot_equity"] - df["other_equity_instruments_PRE"])

    # 按周获取参照日期
    date_ref = w.tdays(begin, end, "Period={}".format(period))
    df = df[df['date'].isin(date_ref.Times)]

    # 保留三列
    df = df[["date","secID",fac]]
   # df['secID'] = sorted(df['secID'])
    #df["date"].apply(lambda x: x.strftime("%Y-%m-%d"))  # 转换日期为字符串格式  原来
    df["date"] = df["date"].apply(lambda x: x.strftime("%Y-%m-%d"))
    return df


def debtequityratio(univ, begin, end, period):
    fac = sys._getframe().f_code.co_name  # 因子名称
    # 数据取自财务报告
    wind_fac = ["tot_equity", "other_equity_instruments_PRE", "tot_non_cur_liab"]
    # 由于财务数据为经常缺失，所以每次获取数据从上一年开始，这样空缺值可以按上一个值填充，若仍为空值则不作修改
    year = int(begin[:4])
    year_pre = year - 1
    begin_p = str(year_pre) + "-12-25"
    # 获取数据
    data = dict()
    for i in wind_fac:
        data[i] = w.wsd(univ, i, begin_p, end, "unit=1;rptType=1;Period={};Fill=Previous".format(period))

    # 整理成DataFrame，按列分别是股票代码、日期和待计算因子值
    col_date = data[wind_fac[0]].Times * len(data[wind_fac[0]].Codes)
    col_code = [[i] * len(data[wind_fac[0]].Times) for i in data[wind_fac[0]].Codes]
    col_code = reduce(lambda x, y: x + y, col_code)
    df = pd.DataFrame({"secID": col_code, "date": col_date})
    for i in wind_fac:  # 按列添加待计算因子值
        col_fac = reduce(lambda x, y: x + y, data[i].Data)
        df[i] = pd.Series(col_fac)

    # 计算因子值：（长期债务合计/(所有者权益-优先股权益)）
    df[fac] = df["tot_non_cur_liab"] / (df["tot_equity"] - df["other_equity_instruments_PRE"])

    # 按周获取参照日期
    date_ref = w.tdays(begin, end, "Period={}".format(period))
    df = df[df['date'].isin(date_ref.Times)]
    #df['secID'] = sorted(df['secID'])
    # 保留三列
    df = df[["date","secID",fac]]

    #df["date"].apply(lambda x: x.strftime("%Y-%m-%d"))  # 转换日期为字符串格式  原来
    df["date"] = df["date"].apply(lambda x: x.strftime("%Y-%m-%d"))
    return df

#"other_equity_instruments_PRE", "tot_non_cur_liab" 数据缺失
def marketvalue_leverage(univ, begin, end, period):
    fac = sys._getframe().f_code.co_name  # 因子名称
    wind_fac = ["ev", "other_equity_instruments_PRE", "tot_non_cur_liab"]
    # 由于财务数据为经常缺失，所以每次获取数据从上一年开始，这样空缺值可以按上一个值填充，若仍为空值则不作修改
    year = int(begin[:4])
    year_pre = year - 1
    begin_p = str(year_pre) + "-12-25"
    # 获取数据
    data = dict()
    data["ev"] = w.wsd(univ, "ev", begin_p, end, "unit=1;Period={};Fill=Previous".format(period))
    data["other_equity_instruments_PRE"] = w.wsd(univ, "other_equity_instruments_PRE", begin, end,
                                                 "unit=1;rptType=1;Period={};Fill=Previous".format(period))
    data["tot_non_cur_liab"] = w.wsd(univ, "tot_non_cur_liab", begin, end,
                                     "unit=1;rptType=1;Period={};Fill=Previous".format(period))

    # 整理成DataFrame，按列分别是股票代码、日期和待计算因子值
    col_date = data[wind_fac[0]].Times * len(data[wind_fac[0]].Codes)
    col_code = [[i] * len(data[wind_fac[0]].Times) for i in data[wind_fac[0]].Codes]
    col_code = reduce(lambda x, y: x + y, col_code)
    df = pd.DataFrame({"secID": col_code, "date": col_date})
    for i in wind_fac:  # 按列添加待计算因子值
        col_fac = reduce(lambda x, y: x + y, data[i].Data)
        df[i] = pd.Series(col_fac)

    # 计算因子值：(市值+优先股+长期债务)/市值
    df[fac] = (df["ev"] + df["other_equity_instruments_PRE"] + df["tot_non_cur_liab"]) / df["ev"]

    # 按周获取参照日期
    date_ref = w.tdays(begin, end, "Period={}".format(period))
    df = df[df['date'].isin(date_ref.Times)]

    # 保留三列
    df = df[["date","secID", fac]]
    #df['secID'] = sorted(df['secID'])
    #df["date"].apply(lambda x: x.strftime("%Y-%m-%d"))  # 转换日期为字符串格式  原来
    df["date"] = df["date"].apply(lambda x: x.strftime("%Y-%m-%d"))
    return df


# univ_2 = ["000650.SZ"]
# univ_1 = ["600036.SH", "000001.SZ", "600015.SH", "601288.SH", "601398.SH", "601818.SH", "601939.SH", "600000.SH"]
# begin_1 = "2017-06-01"
# end_1 = "2017-12-31"
# # fac_df = bias_std_turn_1w(univ_1, begin_1, end_1, "W")
# # print(fac_df)
# mv_fac = MVF(begin_1, end_1)
# print(mv_fac)
