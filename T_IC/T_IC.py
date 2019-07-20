from util import *

def get_T_and_IC(block_name,dict_name_code, beginDate, endDate, Fac, period, filename, r_index_code= '000300.SH'):
    '''
    获取T值，IC值,存为csv文档
    :param block_name: 模块名称'A','cxg'
    :param beginDate: 起始日期
    :param endDate: 终止日期
    :param Fac: 因子列表
    :param period: 周期选择：'M'为月，'W'为周，'D'为天，'Q'为季，'S'为半年，'Y'为年
    :param filename: 生成的csv文件名，'F:/factors/T_IC.csv'
    :param r_index_code: 参照股代码，例'000300.SH'沪深300
    :return: 生成T值、IC值的csv文件
    '''
    row=[]
    trade_calendar = const_trade_calendar(beginDate=beginDate, endDate=endDate, period=period)
    R_index = get_R_index(r_index_code, beginDate, endDate,period)
    for fac in Fac:
        for k,v in fac.items():
            # OLS_params = {}
            WLS_params = {}
            WLS_t_test = {}
            IC = {}
            for date in trade_calendar[:-1]:
            #for date in trade_calendar[:]:
                # 获取当日股票池
                univ = set_universe(block_name, date, dict_name_code)
                univ = st_remove(univ, date)

                date_next = trade_calendar[trade_calendar.index(date) + 1]
                Price_front = get_Pricefront(univ, date)
                Price_behind = get_Pricebehind(univ,date_next)
                # pd.merge()通过按列或索引执行数据库样式的连接操作来合并DataFrame对象。
                R_T = pd.merge(Price_front.loc[:, ['secID', 'front', 'negMarketValue']], Price_behind.loc[:, ['secID', 'behind']],
                               on='secID')
                R_T['W'] = np.sqrt(R_T.negMarketValue)
                R_T['fac_MV'] = standardize_zscore(winsorize_median(R_T.negMarketValue))
                R_T['return'] = np.log(R_T.behind / R_T.front)
                factor_loadings=get_factor_loadings(univ, fac,v, date)


                # 获取行业暴露度 哑变量矩阵
                SW_Industry_List = Stock_Industry(date)
                Linear_Regression = get_Linear_Regression(date, univ, factor_loadings)
                # print(Linear_Regression)

                Linear_Regression = pd.merge(Linear_Regression, R_T.loc[:, ['secID', 'return', 'W', 'fac_MV']], on='secID')
                Linear_Regression.set_index('secID', inplace=True)
                #alter
                Linear_Regression = Linear_Regression.drop_duplicates(subset=[k], keep='first')

                #T值部分
                XT = Linear_Regression.loc[:, SW_Industry_List + [k]]
                #alter
                XT[np.isnan(XT)] = 0
                YT = Linear_Regression['return'] - R_index.loc[date, 'R_index']
                # print('dingwei')
                # print(XT)
                # print('---------------------------')
                # print(YT)
                # WLS回归
                wls = sm.WLS(YT, XT, weights=Linear_Regression.W)
                result = wls.fit()  # 获取拟合结果
                WLS_params[date] = result.params[-1]  # 按date循环取回归系数(因子收益率)，最后一位存的是因子PB，前面存的是行业因子
                WLS_t_test[date] = result.tvalues[-1]  # t值

                #IC部分
                XIC = Linear_Regression.iloc[:, :28]
                XIC['fac_MV'] = Linear_Regression.fac_MV
                # 增加一条
                XIC = XIC.drop_duplicates(subset=[k],keep='first')
                YIC = Linear_Regression.loc[:, k]

                est = sm.OLS(YIC, XIC)
                result = est.fit()
                # 因子 IC 值的计算
                Inf_coeff = R_T.set_index('secID')
                Inf_coeff['Residual'] = result.resid
                m = Inf_coeff.loc[:, ['Residual', 'return']].corr().iloc[0, 1]
                IC[date] = m

            #-----------------------------------------------------------------------------------
            WLS = pd.Series(WLS_params)
            t_test = pd.Series(WLS_t_test)
            print("WLS_params:",WLS_params)
            t_mean = np.sum(np.abs(t_test.values)) / len(t_test)
            print('t值序列绝对值平均值', t_mean)
            n = [x for x in t_test.values if np.abs(x) > 2]  # 筛选>2的x值
            t_over_two_per = '%.4f' %(len(n) / len(t_test))
            print('t值序列绝对值大于2的占比——判断因子的显著性是否稳定', t_over_two_per)
            wls_mean = WLS.mean()
            print('因子收益率序列平均值', wls_mean)
            t_zero_check = WLS.mean() / (WLS.std() / np.sqrt(len(WLS) - 1))                 # t=（x均值-u）/（方差/根号（n-1））
            print('该均值零假设检验的t值', t_zero_check)
            t_absmean_divid_std = np.abs(t_test.mean()) / t_test.std()
            print('t值序列均值的绝对值除以t值序列的标准差', t_absmean_divid_std)
            #-----------------------------------------------------------------------------------
            IC = pd.Series(IC)
            ic_mean = IC.mean()
            ic_mean_abs = np.mean(np.abs(IC))
            print('IC 值序列的均值大小', ic_mean, 'IC 值序列绝对值的均值大小', ic_mean_abs)
            ic_std = IC.std()
            print('IC 值序列的标准差', ic_std)
            ic_mean_divid_std = IC.mean() / IC.std()
            print('IR 比率（IC 值序列均值与标准差的比值）', ic_mean_divid_std)
            n = [x for x in IC.values if x > 0]
            ic_over_zero_per =  '%.4f' % (len(n) / len(IC))
            print('IC 值序列大于0的占比', ic_over_zero_per)
            n = [x for x in IC.values if x > 0.2]
            ic_over_zeropointtwo_per = '%.4f' % (len(n) / len(IC))
            print('IC 值序列大于0.2的占比', ic_over_zeropointtwo_per)

            row.append([t_mean,t_over_two_per,wls_mean,t_zero_check,t_absmean_divid_std,
                        ic_mean,ic_mean_abs,ic_std,ic_mean_divid_std,ic_over_zero_per,ic_over_zeropointtwo_per])
            # row.append([t_mean, wls_mean, t_zero_check, t_absmean_divid_std,
            #   ic_mean,ic_mean_abs,ic_std,ic_mean_divid_std])
            # 输出按月的PB因子t检验结果
            # t_test.plot('bar', figsize=(16, 5))
            # plt.show()
    list = []
    for fac in Fac:
        for k in fac.keys():
            list.append(k)
    df = pd.DataFrame(row, index=list,columns=['|t|均值','|t|>2占比','因子收益率序列平均值','因子收益率序列t检验','|t|均值/t标准差',
                                             'IC序列均值','|IC|均值','IC序列标准差','IR比率','IC>0占比','|IC|>0.02占比'])
    df.to_csv(filename,float_format='%.5f',encoding="gbk",mode='w')
#-----------------------------------------------
"""
主函数，输出检验结果表。
获取T值和IC值，生成结果为格式如[因子名称，'|t|均值','|t|>2占比','因子收益率序列平均值','因子收益率序列t检验','|t|均值/t标准差', 'IC序列均值','|IC|均值','IC序列标准差','IR比率','IC>0占比','|IC|>0.02占比']的csv文件.
"""
w.start()
print(w.isconnected())
# ---------------------------------------
block_name='B'                                    #股池名称
dict_name_code = {'A': 'a001010100000000',      # A股
                  'B': 'a001010600000000',      # B股
                  'shA': 'a001010200000000',    # 沪市A股
                  'szA': 'a001010300000000',    # 深证A股
                  'zxqyb': '1000009396000000',  # 中小企业板
                  'cyb': 'a001010r00000000'}    # 创业板
beginDate = "2015-02-01"                         #起始日期
endDate = "2015-10-01"                           #终止日期
#Fac = [{'PB':3},{'PE':10},{'PS':2}]              #wind取出的因子名称key='PB',value='ruleType'
Fac = [{'FCFP':'a'},{'EPcut':'a'}]              #因子名称key='EPcut'计算出来的因子，value='a'为判断是否为计算出来的因子
period = 'Q'                                      #周期选择:'M'为月，'W'为周，'D'为天，'Q'为季，'S'为半年，'Y'为年
r_index_code= '000010.SH'                        #基准
filename='F:/factors/T_IC.csv'                  #csv结果文件绝对路径
# ---------------------------------------
get_T_and_IC(block_name,dict_name_code, beginDate, endDate, Fac, period, filename, r_index_code= r_index_code)
w.stop()