import pandas as pd, subprocess
df = pd.read_csv('/mnt/user-data/uploads/AirQualityUCI.csv', encoding='utf-8-sig').dropna(how='all').iloc[:, :15]
df['measured_at'] = pd.to_datetime(df['Date']+' '+df['Time'], format='%m/%d/%Y %H:%M:%S')
params = [
 ('CO(GT)','True hourly avg CO concentration','mg/m3','reference','CO'),
 ('PT08.S1(CO)','Tin oxide sensor response (CO)','sensor resp.','sensor','CO'),
 ('NMHC(GT)','True hourly avg non-methane hydrocarbons','ug/m3','reference','NMHC'),
 ('C6H6(GT)','True hourly avg benzene','ug/m3','reference','C6H6'),
 ('PT08.S2(NMHC)','Titania sensor response (NMHC)','sensor resp.','sensor','NMHC'),
 ('NOx(GT)','True hourly avg NOx','ppb','reference','NOx'),
 ('PT08.S3(NOx)','Tungsten oxide sensor response (NOx)','sensor resp.','sensor','NOx'),
 ('NO2(GT)','True hourly avg NO2','ug/m3','reference','NO2'),
 ('PT08.S4(NO2)','Tungsten oxide sensor response (NO2)','sensor resp.','sensor','NO2'),
 ('PT08.S5(O3)','Indium oxide sensor response (O3)','sensor resp.','sensor','O3'),
 ('T','Temperature','degC','weather',None),
 ('RH','Relative humidity','%','weather',None),
 ('AH','Absolute humidity','g/m3','weather',None)]
pid = {p[0]: i+1 for i,p in enumerate(params)}
long = df.melt(id_vars='measured_at', value_vars=list(pid), var_name='code', value_name='value')
long = long[long['value'] != -200]          # -200 is the dataset's "missing" marker -> row is simply not stored
long['parameter_id'] = long['code'].map(pid); long['station_id'] = 1
long[['station_id','parameter_id','measured_at','value']].to_csv('meas.csv', index=False)
with open('seed.sql','w') as f:
    f.write("INSERT INTO stations(station_name,country,setting,first_reading,last_reading) VALUES "
            f"('Italian city air-quality station','Italy','Road level, significantly polluted area','{df.measured_at.min()}','{df.measured_at.max()}');\n")
    for c,d,u,cat,p in params:
        f.write("INSERT INTO parameters(code,description,unit,category,pollutant) VALUES (%s);\n" %
                ",".join("NULL" if x is None else "'%s'"%x for x in (c,d,u,cat,p)))
print(len(df), len(long))
