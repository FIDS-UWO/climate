% PROGRAM TO GENERATE MULTI-VARIATE MULTI-SITE WEATHER DATA
% ROSHAN K SRIVASTAVA
% CREATED ON: JULY 25, 2013
% Modified By: SOHOM MANDAL
% Modification Date: March 1, 2017

clear all
close all
clc
% Number of Replicates: User specific; Use a Positive interger
prompt = {'Please provide number of replicates (should be an integer):'};
dlg_title = 'Input';
num_lines = 1;
defaultans = {'2'};
answer =(inputdlg(prompt,dlg_title,num_lines,defaultans));
numrep = str2num(answer{:}); 
if isnan(numrep) || fix(numrep) ~= numrep
  disp('Please enter a positive integer ')
end
disp('Code is running! Please wait');
%File name reading
z=dir('*pr*.csv'); % Reading precipitation files name
z1=dir('*tasmax*.csv'); %  Reading maximum temperature files name 
z2=dir('*tasmin*.csv'); % Reading minimum temperature files name
% Working through the files
for j=1:length(z)
%     h = waitbar(length(z),'Downsacling');
    varname_pr=z(j).name; 
    varname_tmax=z1(j).name; 
    varname_tmin=z2(j).name; 
    expression = ('\_');
    splitStr_pr=regexp(varname_pr,expression,'split'); % split the Pr files name using '_' as regular expression
    splitStr_tmax=regexp(varname_tmax,expression,'split'); % split the Tmax files name using '_' as regular expression
    splitStr_tmin=regexp(varname_tmin,expression,'split'); % split the Tmin files name using '_' as regular expression
    m1=strcmp(strcat(splitStr_pr(3),splitStr_pr(5),splitStr_pr(6)),strcat(splitStr_tmax(3),splitStr_tmax(5),splitStr_tmax(6)));
    m2=strcmp(strcat(splitStr_tmax(3),splitStr_tmax(5),splitStr_tmax(6)),strcat(splitStr_tmin(3),splitStr_tmin(5),splitStr_tmin(6)));
    if m1==1 && m2==1 % Compare files name
 
% LOAD YOUR INPUT FILES
% Each file contains data for a particular weather variable
% NOTE: Rows and Colums represent time and stations respectively
    [ppt header1]=xlsread(z(j).name); %Read Precipitation data
    tmax=csvread(z1(j).name,1,3); %Read Maximum temperature data
    tmin=csvread(z2(j).name,1,3); %Read Minimum temperature data
    [r,c] = size(ppt);
    % Modify this depending on the number of variables added
    data_all = [ppt(:,4:end)+0.1 tmax+273.15 tmin+273.15];
     
    % DO NOT MODIFY ANY THING FROM HERE IF YOU ARE NOT SURE
    date=repmat(ppt(:,1:3),numrep,1);
    numobs = length(data_all);
    [m1,n1] = size(data_all);
    [data_all_std,data_all_mu,data_all_sig] = zscore(data_all);
    [loadings, scores, variances, tscores] = princomp(data_all_std);
    rand('state',0);
    cm = 1;
    [sc_fit,debug] = MBE_RKS(scores(:,cm),numrep,[],[],1,1);
    scores_fit = scores;
    loadings_fit = loadings;
    sds = data_all_sig;
    means=data_all_mu;
    c1 =[];
    for i = 1:numrep
        scores_fit(:,cm) = sc_fit(:,i);
        b1 = loadings_fit*scores_fit';
        d1 = (b1' .*  repmat(sds,numobs,1) + repmat(means,numobs,1));
        d1(d1(:,1:22)<0)=0;
        c1 = [c1;d1];
        d1=[];b1=[];
    end
    % WRITE OUTPUT FILE
    newname=strcat('MBE','_',splitStr_pr(3),'_', splitStr_pr(5),'_',splitStr_pr(6)); % Create output file name; User can modify 
    c1=[date c1(:,1:10) c1(:,11:end)-273.15];
    %Pr= Precipitation; Tasmax=Maximum Temperature; 
    %Tasmin=Minimum Temperature; Header will look like:  "Pr_(Station Name)"
    mod_header=horzcat(header1(:,1:3),strcat('Pr_',header1(:,4:end)),strcat('Tasmax_',header1(:,4:end)),strcat('Tasmin_',header1(:,4:end))); % Change the header if more than three variables are used 
    filename= cell2mat(strcat(newname, '.csv'));
    csvwrite_with_headers(filename,c1, mod_header);% Writes the output file into csv format
    else 
        fprintf(2,'Error: GCM files are not matching!!\n') % Error message for not matching the GCMs file
    end
    
 end
msgbox('Downscaling Completed'); % message box for complete the work 


