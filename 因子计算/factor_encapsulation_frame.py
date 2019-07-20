#因子封装函数，生成的结果为格式如[股票代码，日期，因子1，因子2，……]的csv文件，其中函数调用utils.py，因子计算调用
#factorls_pool
from utils import *
from factors_pool import *
def fac_encapsulation_frame(begin, end, period, Fac, file_prefix, block_name ,dict_name_code):
    '''
    因子值封装为csv文件
    :param begin: 起始日期
    :param end: 结束日期
    :param Fac: 因子列表
    :param period: 周期
    :param filename: 得到的文件名
    :param block_name: 股池名称，'A'为全A股，'cxg'为次新股，详情可见utils的set_universe函数
    :return: csv文件
    '''
    trade_calendar = const_trade_calendar(beginDate=begin, endDate=end, period=period)  # 获取交易日历
    target = {}
    # 求全A股时用这个部分
    for date in trade_calendar:  # 每日股池，存为dict
        univ = set_universe(block_name, date,dict_name_code)
        univ = st_remove(univ, date)
        target[date] = univ
    # target = read_txt(filename='C:/Users/MSI-PC/Desktop/datasets/universe_cxg_calendar.txt',
    #                        readmode='r')  # 函数来自header,文件来自univ_industry_txt中生成的文件，返回一个dict
    # 用于获得该日历期间的所有股票代码，保存为stock_list，stk_list相当于前者的set
    stk_list=[]
    for key in target.keys():
        stk_list = list(set(stk_list+target[key]))
    #原来
    #stock_list = sorted(stk_list*len(list(target.keys())))
    #stock_list = regain_suffix(stock_list)
    # 用于获得日期列表
    #date_list = list(target.keys()) * len(stk_list)
    #修改
    stock_list = sorted(stk_list * len(list(target.keys())))
    stock_list = regain_suffix(stock_list)
    # 用于获得日期列表
    date_list = sorted(list(target.keys())*len(stk_list))

    #由于返回的因子值DataFrame为三列格式[secID,date,fac]，初始化一个df_tocsv包含两列(secID,date)，
    # 合并df即为通过secID和date的键值组合锁定对应值，从而做到准确添加对应值
    #原来
    #df_tocsv = pd.DataFrame({"secID": stock_list, "date": date_list})
    #修改
    df_tocsv = pd.DataFrame({ "date": date_list,"secID": stock_list})

    hb=1
    for fac in Fac:
        # df_fac = fac(regain_suffix(list(dealed.keys())), begin, end, period)
        #原来
        # df_fac = fac(regain_suffix(stk_list), begin, end, period)
        # df_tocsv = pd.merge(df_tocsv, df_fac, on=['secID', 'date'])
        #修改
        df_fac = fac(regain_suffix(stk_list), begin, end, period)
        df_tocsv = pd.merge(df_tocsv, df_fac, on=[ 'date','secID'])

        print('生成的第',hb,'个因子')
        hb+=1
    #原来
    #df_tocsv.to_csv(file_prefix+'fac_value.csv', float_format='%.5f', mode='w', index=0)   #写入csv文件
    #修改
    df_tocsv = df_tocsv.drop_duplicates(subset=['date', 'secID'], keep='first')
    df_tocsv.to_csv(file_prefix + 'fac_value.csv', float_format='%.5f', mode='w', index=0)  # 写入csv文件

w.start()
print(w.isconnected())
#----可定义参数----------------------------------------
beginDate = "2015-02-01"    #起始日期
endDate = "2015-10-01"      #终止日期
period = 'Q'                 #周期选择：'M'为月，'W'为周，'D'为天，'Q'为季，'S'为半年，'Y'为年
Fac = [EPcut,FCFP]               #因子名称
#因子池
# [EPcut, FCFP, rating_change, rating_targetprice, std_turn_1w, std_turn_2w, std_turn_4w, std_turn_12w,
# bias_std_turn_1w, bias_std_turn_2w, bias_std_turn_4w, weighted_strength_1w, weighted_strength_2w,
# weighted_strength_4w, weighted_strength_12w, exp_wgt_return_1w, exp_wgt_return_2w, exp_wgt_return_4w,
# exp_wgt_return_12w, HAlpha, beta_consistence, id1_std_3m, id2_std_3m, id2_std_up_3m, id2_std_down_3m,
#  high_r_std_3m, low_r_std_3m, hml_r_std_3m, hpl_r_std_3m, financial_leverage,debtequityratio, marketvalue_leverage]

file_prefix = 'F:/factors/' #存放csv文件目录
block_name = 'B'              #股池名称
dict_name_code = {'A': 'a001010100000000',  # A股
                  'B': 'a001010600000000',  # B股
                  'shA': 'a001010200000000',  # 沪市A股
                  'szA': 'a001010300000000',  # 深证A股
                  'zxqyb': '1000009396000000',  # 中小企业板
                  'cyb': 'a001010r00000000'}  # 创业板
#--------------------------------------------------------
fac_encapsulation_frame(beginDate, endDate, period, Fac, file_prefix, block_name,dict_name_code)
w.stop()

'''
   旧思路，不适用
   dealed = {}  # 初始化，该段将上段的dict的股票代码和日期列转换过来，{secID：date}
   for i, item1 in enumerate(target):
       for j, item2 in enumerate(target[item1]):
           if dealed.get(item2) is None:
               dealed[item2] = []
               dealed[item2].append(item1)
           else:
               dealed[item2].append(item1)
   print(dealed)
   stock_list = []  # stock_list为股票列表
   for i in dealed:  # date_list为日期列表
       for j in range(len(dealed[i])):
           stock_list.append(i)
   print(len(stock_list))
   date_list = reduce(operator.add, dealed.values())
   print(len(date_list))
   '''
'''
另一种思路，不易实现
df_tocsv = pd.DataFrame({"secID": stock_list, "date": date_list})
# 对因子列表中的每一个因子，首先初始化整个fac对应的列的dataframe：df_fac，然后对每一支股票，调用对应函数，
# 得到整列中某股所在部分的dataframe：df_stk，再将df_stk添加到df_fac中。最后将df和df_fac进行横向联结，得到应写入csv中的
# dataframe：df
for fac in Fac:
    df_fac = pd.DataFrame()
    for stk in dealed:
        df_stk = pd.DataFrame({getattr(fac, '__name__'): fac(stk, begin, end, period)})
        df_fac.append(df_stk, ignore_index=True)
        # df_stk = fac(stk, begin, end, period)
        # df_tocsv = pd.merge(df_tocsv, df_stk, on=['secID', 'date'])
    df_tocsv = pd.concat([df_tocsv, df_fac], axis=1)
'''











