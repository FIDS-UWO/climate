function y = betalik(vP, mX, vy)
k = length(vP);
eta = mX*vP(1:k-1); 
mu = exp(eta) ./ (1+exp(eta)); 

phi = vP(k);
y = -sum( gammaln(phi) - gammaln(mu*phi)- gammaln(abs(1-mu)*phi) + ((mu*phi-1) .* log(vy)) + ( (1-mu)*phi-1 ) .* log(1-vy) );


