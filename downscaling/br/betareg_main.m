%IF YOU NOT SURE PLEASE DON'T CHNAGE ANYTHING HERE
function [vP, muhat]= betareg(vy, mX)
format short g;
n = length(vy);
p = size(mX,2);

if(max(vy) >= 1 || min(vy) <= 0) 
    error(sprintf('\n\nERROR: DATA OUT OF RANGE (0,1)!\n\n')); 
end

if(p >= n) 
     error(sprintf('\n\nERROR: NUMBER OF COVARIATES CANNOT EXCEED NUMBER OF OBSERVATIONS!\n\n'));
end

ynew = log( vy ./ (1-vy) );


if(p > 1) 
     betaols = (mX \ ynew); 
elseif(p==1) 
     betaols = (mean(ynew));
end

olsfittednew = mX*betaols; 

olsfitted = exp(olsfittednew) ./ (1 + exp(olsfittednew)); 
olserrorvar = sum((ynew-olsfittednew).^2)/(n-p); 

ybar = mean(vy); 
yvar = var(vy);   

% starting values
vps = [betaols;(mean(((olsfitted .* (1-olsfitted))./olserrorvar)-1))];
options = optimset('Display','off');
vP = fminsearch(@(vP) betalik(vP, mX, vy), abs(vps),options);
% k_OptimOptions = optimset('Display','off');
etahat = mX*vP(1:p); 
muhat = exp(etahat ) ./ (1+exp(etahat)); 
phihat = vP(p+1); 
end
