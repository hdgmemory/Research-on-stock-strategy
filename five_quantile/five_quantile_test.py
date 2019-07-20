from univ_industry_txt import *
from utils import *

def get_previous_date(start, end, current_date):
    '''
    获取当前交易日的前一个交易日
    :param start:起始日期
    :param end:结束日期
    :param current_date:当前交易日
    :return: previous_date前一个交易日
    '''
    trade_days = w.tdays(start, end, "")
    day_list = [v.strftime('%Y-%m-%d') for v in trade_days.Data[0]]
    previous_date = day_list[day_list.index(current_date) - 1]
    return previous_date

def get_five_quantile_csv(Fac, start, end, period, to_where,dict_name_code,block_name):
    '''
    获取五分位回测所需要的csv文件
    :param fac: 因子名称
    :param start: 起始日期
    :param end: 结束日期
    :param period: 周期
    :param to_where:保存文件的路径
    :param dict_name_code: 股票池
    :param block_name:股池名称
    :return: csv
    '''
    for fac in Fac:
        for k,v in fac.items():
            trade_calendar = const_trade_calendar(beginDate=start, endDate=end, period=period)
            cxg = get_my_cxg_universe(trade_calendar,sectorid)
            Industry = get_industry(trade_calendar, my_universe)
            #用于存储计算生成的各行，最后用于存入dataframe
            row_holding_list = []
            row_industry = []
            row_holding = []
            row_neu_weights = []
            row_neu_sum = []
            for quantile_five in range(0, 5):
                print("quantile_five:",quantile_five)
                for date in trade_calendar:
                    print("date:",date)
                    univ = cxg[date]
                    re_univ = regain_suffix(univ)#用于适配万得接口，将后缀改回'SH','SZ'形式

                    # 判断行业分类
                    Constituent_Stocks = Industry[date] #数据来自35行，获取date日的所有行业的成分股{'6101000000000000': ['603363.SH'],……}

                    # 获取因子数据
                    previous_date = get_previous_date(start, end, date)
                    factor = get_factor(re_univ, k,v, previous_date, file_prefix=to_where)

                    # 按行业排序筛选，得出行业不为空的所有的行业
                    holding_list = []
                    holding = {}
                    Industrys_list = []
                    for index in Constituent_Stocks:
                        Industrys_list.append(index)
                    for s in Industrys_list:
                        tmp = Constituent_Stocks[s]  # 行业s的所有股票
                        tmp = factor.loc[tmp, :]  # 以上得出的股票的因子值
                        tmp.sort_values(k, inplace=True)  # 按fac因子值进行排序
                        q_min = tmp.quantile(quantile_five * 0.2)[k]
                        q_max = tmp.quantile((quantile_five + 1) * 0.2)[k]
                        industry_univ = tmp[tmp[k] >= q_min][tmp[k] <= q_max]  # 因子值在这一个分位的s行业的股票，且去掉极值
                        industry_univ = industry_univ.index.values.tolist() #获取行业s的股池
                        holding[s] = industry_univ  # 经因子值筛选后，在quantile_five这个分位的s行业的成分股
                        row_holding.append([quantile_five, date, s]+industry_univ)
                        holding_list = holding_list + industry_univ  # 这一分位的所有股票

                    # 伪行业中性
                    neu_weights = {}
                    neu = set_universe(dict_name_code,block_name,previous_date)

                    # 以上两个指数股票的流通市值
                    d = w.wss(neu, "windcode,mkt_cap_float",
                              "tradeDate={};priceAdj=U;cycle=D;unit=1;currencyType=".format(previous_date))
                    temp = {
                        'secID': replace_suffix(d.Data[0]),
                        'negMarketValue': d.Data[1]
                    }
                    tmp = pd.DataFrame(temp)
                    tmp.set_index('secID', inplace=True)
                    neu = replace_suffix(neu)
                    Industrys_list = []
                    for index in holding.keys():
                        Industrys_list.append(index)
                    for s in Industrys_list:
                        cm = list(set(neu).intersection(set(holding[s])))
                        cm = tmp.loc[cm]
                        cm = cm.negMarketValue.sum()  # s行业流通市值的总和
                        neu_weights[s] = cm
                        row_neu_weights.append([quantile_five, date, s, cm])
                    neu_sum = pd.Series(neu_weights).sum()  # 所有行业流通市值的总和
                    row_neu_sum.append([quantile_five, date, neu_sum])
                    row_holding_list.append([quantile_five,date]+holding_list)
                    row_industry.append([quantile_five,date]+list(holding.keys()))
            if not os.path.exists(to_where+str(k)):
                os.makedirs(to_where+str(k))
            df = pd.DataFrame(row_holding_list, index=trade_calendar*5)
            df.to_csv(to_where+str(k)+'/'+str(k)+'_holdinglist.csv',mode='w',header=0,index=0)
            df = pd.DataFrame(row_industry, index=trade_calendar*5)
            df.to_csv(to_where+str(k)+'/'+str(k)+'_industrylist.csv', mode='w', header=0, index=0)
            df = pd.DataFrame(row_holding)
            df.to_csv(to_where+str(k)+'/'+str(k)+'_holding.csv',mode='w',header=0,index=0)
            df = pd.DataFrame(row_neu_weights)
            df.to_csv(to_where+str(k)+'/'+str(k)+'_neu_weights.csv',mode='w',header=0,index=0)
            df = pd.DataFrame(row_neu_sum)
            df.to_csv(to_where+str(k)+'/'+str(k)+'_neu_sum.csv',mode='w',header=0,index=0)
"""
先进入univ_industry_txt文件，调整参数，点击运行生成txt，之后进入five_quantile_test文件，
调整参数和之前的一致，点击运行即可。之后将生成的csv文件和txt文件上传到优矿平台，选择final
五分位文件，调整参数和前方参数一致，依次点击运行，直至最后一个代码块产生图像
"""
#生成用于五分位测试的csv文件，每个因子建立一个以因子名命名的文件夹，每个文件夹中包含五个csv文件，
#str(fac)_holdinglist,str(fac)_industrylist,str(fac)_holding,str(fac)_neu_weights,str(fac)_neu_sum
w.start()
print(w.isconnected())
#--------------------------------------------------------
Fac = [{'PB':3},{'PE':10},{'PS':2}]        #因子名称key='PB',value='ruleType'
start = '2015-01-01'                       # 回测起始时间
end = '2015-02-01'                         # 回测结束时间
period = 'M'                                #周期选择:'M'为月，'W'为周，'D'为天，'Q'为季，'S'为半年，'Y'为年
block_name = 'B'                            #股池名称
dict_name_code = {'A': 'a001010100000000',  # A股
                  'B': 'a001010600000000',  # B股
                  'shA': 'a001010200000000',  # 沪市A股
                  'szA': 'a001010300000000',  # 深证A股
                  'zxqyb': '1000009396000000',  # 中小企业板
                  'cyb': 'a001010r00000000'}  # 创业板
to_where = 'F:/factors/'
#--------------------------------------------------------
get_five_quantile_csv(Fac, start, end, period, to_where,dict_name_code,block_name)

w.stop()